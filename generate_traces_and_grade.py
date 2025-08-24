import json
import os
import re
import time
from tqdm import tqdm
from datetime import datetime
from openai import OpenAI
from prompts import REASONING_PROMPT, QUIZ_GRADING_PROMPT

# --- Configuration ---
# API credentials (MUST BE FILLED IN BY THE USER)
COMMERCIAL_API_KEY = "YOUR_API_KEY_HERE" 
COMMERCIAL_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1" # Or your endpoint

# Models
GRADER_MODEL = "qwen-turbo" 
REASONER_MODELS = [
    {
        "model_id": "deepseek-r1",
        "type": "expert",
        "num_traces": 2,
        "temperature": 0.3
    },
    {
        "model_id": "qwen2-72b-instruct",
        "type": "peer",
        "num_traces": 2,
        "temperature": 0.7
    },
    {
        "model_id": "qwen2-7b-instruct",
        "type": "student",
        "num_traces": 2,
        "temperature": 0.9
    }
]

# File I/O
INPUT_FILE = "OpenR1-Math_with_quizzes.jsonl" 
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DETAILS_FILE = f"run_details_{RUN_TIMESTAMP}.jsonl"
OUTPUT_OVERVIEW_FILE = f"run_overview_{RUN_TIMESTAMP}.json"

# Script Behavior
PROBLEMS_TO_PROCESS = 100

# --- API Client and Helper Functions ---
client = OpenAI(api_key=COMMERCIAL_API_KEY, base_url=COMMERCIAL_API_URL, max_retries=2)

def call_llm_api(prompt, model_id, temperature=0.3):
    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2048,
            timeout=300.0,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"    API Error with model {model_id}: {e}")
        return None

def parse_json_from_text(text):
    if not text: return None
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None

def extract_boxed_answer(trace_text):
    if not trace_text: return None
    match = re.search(r"\\boxed\{(.*?)\}", trace_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def normalize_and_compare_answers(extracted_answer_raw, ground_truth_answers_list):
    if extracted_answer_raw is None or not ground_truth_answers_list:
        return False
    def normalize(text):
        s = str(text).strip().lower()
        s = re.sub(r'\\(d?frac)\s*\{([^}]+)\}\s*\{([^}]+)\}', r'\2/\3', s)
        s = re.sub(r'\\[a-zA-Z]+', '', s)
        s = re.sub(r'\s+', '', s)
        s = re.sub(r'^[(\[{]*|[])}\$]*$', '', s)
        return s
    norm_extracted = normalize(extracted_answer_raw)
    for gt_answer in ground_truth_answers_list:
        norm_ground_truth = normalize(gt_answer)
        if norm_extracted == norm_ground_truth:
            return True
        try:
            def evaluate_numeric(val):
                if '/' in val:
                    parts = val.split('/')
                    if len(parts) == 2: return float(parts[0]) / float(parts[1])
                return float(val)
            if abs(evaluate_numeric(norm_extracted) - evaluate_numeric(norm_ground_truth)) < 1e-6:
                return True
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    return False

# --- Main Orchestration with Graceful Shutdown ---
def run_full_evaluation():
    try:
        all_problems = []
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                all_problems.append(json.loads(line))
    except FileNotFoundError:
        print(f"FATAL: Input file not found at '{INPUT_FILE}'")
        return

    detailed_results = []
    
    try:
        problems_to_run = all_problems[:PROBLEMS_TO_PROCESS]
        for problem_data in tqdm(problems_to_run, desc="Evaluating Problems"):
            problem_id = problem_data.get('uuid')
            question = problem_data.get('problem')
            ground_truth_raw_str = str(problem_data.get('answer'))
            ground_truth_answers_list = [ans.strip() for ans in re.split(r'\s+or\s+|\s*,\s*|\s*;\s*', ground_truth_raw_str)]
            
            quiz_json = problem_data.get('quiz')
            if not quiz_json:
                continue

            for reasoner_config in REASONER_MODELS:
                model_id = reasoner_config["model_id"]
                model_type = reasoner_config["type"]
                num_traces = reasoner_config["num_traces"]
                temperature = reasoner_config["temperature"]

                for i in range(num_traces):
                    reasoner_prompt = REASONING_PROMPT.format(problem=question)
                    reason_trace = call_llm_api(reasoner_prompt, model_id, temperature)
                    extracted_answer = extract_boxed_answer(reason_trace)
                    is_correct = normalize_and_compare_answers(extracted_answer, ground_truth_answers_list)

                    grading_prompt = QUIZ_GRADING_PROMPT.format(
                        quiz_json_text=json.dumps(quiz_json, indent=2),
                        reasoner_trace_text=reason_trace
                    )
                    raw_grading_output = call_llm_api(grading_prompt, GRADER_MODEL)
                    grading_result = parse_json_from_text(raw_grading_output)
                    
                    reward_score = 0.0
                    if grading_result and "Score" in grading_result:
                        score_match = re.search(r'(\d+\.?\d*)', str(grading_result.get("Score")))
                        if score_match:
                            reward_score = float(score_match.group(1))

                    result_record = {
                        "problem_id": problem_id, "question": question, "ground_truth_answer": ground_truth_raw_str,
                        "generator_model": model_id, "generator_type": model_type, "trace_num": i + 1,
                        "is_correct": is_correct, "extracted_answer": extracted_answer,
                        "reward_score": reward_score, "reason_trace": reason_trace, "grading_result": grading_result,
                    }
                    detailed_results.append(result_record)
                    
                    with open(OUTPUT_DETAILS_FILE, 'a', encoding='utf-8') as f_details:
                        f_details.write(json.dumps(result_record) + '\n')
                    time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nKEYBOARD INTERRUPT DETECTED! Saving progress...")
    
    # --- Final Analysis ---
    if not detailed_results:
        print("No results were processed. Exiting.")
        return

    total_traces = len(detailed_results)
    total_correct = sum(1 for r in detailed_results if r['is_correct'])
    accuracy = (total_correct / total_traces * 100) if total_traces > 0 else 0
    # ... (rest of summary generation)

    with open(OUTPUT_OVERVIEW_FILE, 'w', encoding='utf-8') as f_overview:
        json.dump(overview_data, f_overview, indent=4)
        
    print(f"\n✅ Evaluation Complete (or Gracefully Stopped)!")
    print(f"  - Full details saved to: {OUTPUT_DETAILS_FILE}")
    print(f"  - Overview saved to: {OUTPUT_OVERVIEW_FILE}")

if __name__ == "__main__":
    run_full_evaluation()
