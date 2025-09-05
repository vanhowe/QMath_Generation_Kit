import json
import os
import re
import time
from tqdm import tqdm
from datetime import datetime
from openai import OpenAI
# Make sure you have a prompts.py file with these variables defined
from prompts import REASONING_PROMPT, QUIZ_GRADING_PROMPT

# --- Configuration ---

# -- API Endpoints & Keys (Collaborator MUST configure this section) --
GRADER_API_URL = "YOUR_DEEPSEEK_V3_API_URL_HERE"
GRADER_API_KEY = "YOUR_DEEPSEEK_API_KEY_HERE" 
GRADER_MODEL = "deepseek-chat" # Ensure this is the correct model name

LOCAL_API_URL_PEER = "http://localhost:8000/v1"
LOCAL_API_KEY_PEER = "EMPTY"

LOCAL_API_URL_STUDENT = "http://localhost:8001/v1"
LOCAL_API_KEY_STUDENT = "EMPTY"

# --- Portfolio of Reasoner Models ---
# The script will use these configurations to generate new reasoning traces.
REASONER_MODELS = [
    {
        "type": "expert",
        "source": "pre_generated",
        "num_traces": 2 # Will use up to 2 traces from the input file's 'valid_reasoning_traces'
    },
    {
        "type": "peer",
        "source": "api_call",
        "model_id": "Qwen/Qwen2.5-72B-Instruct",
        "api_url": LOCAL_API_URL_PEER,
        "api_key": LOCAL_API_KEY_PEER,
        "num_traces": 2,
        "temperature": 0.7
    },
    {
        "type": "student",
        "source": "api_call",
        "model_id": "Qwen/Qwen2.5-7B-Instruct",
        "api_url": LOCAL_API_URL_STUDENT,
        "api_key": LOCAL_API_KEY_STUDENT,
        "num_traces": 2,
        "temperature": 0.9
    }
]

# --- MODIFIED: File I/O & Script Behavior ---
# The script now reads from the single JSONL file produced by the quiz generation step.
INPUT_FILE = "/root/autodl-tmp/math_data_with_quizzes.jsonl" 

# Output will be organized by a timestamp for each run
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_BASE_DIR = f"results/run_{RUN_TIMESTAMP}"
OUTPUT_DETAILS_FILE = os.path.join(OUTPUT_BASE_DIR, "run_details.jsonl")
OUTPUT_OVERVIEW_FILE = os.path.join(OUTPUT_BASE_DIR, "run_overview.json")


# --- IMPROVEMENT: Pre-initialize API clients for efficiency ---
print("Initializing API clients...")
API_CLIENTS = {
    "grader": OpenAI(api_key=GRADER_API_KEY, base_url=GRADER_API_URL, max_retries=3, timeout=300.0),
    "peer": OpenAI(api_key=LOCAL_API_KEY_PEER, base_url=LOCAL_API_URL_PEER, max_retries=3, timeout=300.0),
    "student": OpenAI(api_key=LOCAL_API_KEY_STUDENT, base_url=LOCAL_API_URL_STUDENT, max_retries=3, timeout=300.0)
}
print("API clients initialized.")


# --- MODIFIED: Helper Functions now use pre-initialized clients ---
def call_llm_api(client_key, prompt, model_id, temperature):
    """Uses a pre-initialized client to call an OpenAI-compatible API."""
    try:
        client = API_CLIENTS[client_key]
        completion = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2048
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"    API Error using client '{client_key}' for model {model_id}: {e}")
        return None

# --- Helper Functions (Unchanged logic) ---
def extract_boxed_answer(trace_text):
    if not trace_text: return None
    match = re.search(r"\\boxed\{(.*?)\}", trace_text, re.DOTALL)
    if match: return match.group(1).strip()
    return None

def parse_json_from_text(text):
    if not text: return None
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except json.JSONDecodeError: return None
    return None

def normalize_and_compare_answers(extracted_answer_raw, ground_truth_answers_list):
    if extracted_answer_raw is None or not ground_truth_answers_list: return False
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
        if norm_extracted == norm_ground_truth: return True
        try:
            def evaluate_numeric(val):
                if '/' in val:
                    parts = val.split('/'); return float(parts[0]) / float(parts[1])
                return float(val)
            if abs(evaluate_numeric(norm_extracted) - evaluate_numeric(norm_ground_truth)) < 1e-6: return True
        except (ValueError, TypeError, ZeroDivisionError): pass
    return False

# --- MODIFIED: Main Orchestration now reads and writes JSONL files ---
def run_full_evaluation():
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    
    if not os.path.exists(INPUT_FILE):
        print(f"FATAL: No input file found at '{INPUT_FILE}'. Please run 'generate_quizzes.py' first.")
        return

    all_detailed_results = []
    
    try:
        # Open both input and output files to stream data
        with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
             open(OUTPUT_DETAILS_FILE, 'w', encoding='utf-8') as f_details:
            
            # Create a list of problems to get an accurate total for tqdm
            problems_to_process = list(f_in)
            print(f"Found {len(problems_to_process)} problems with quizzes to evaluate.")

            for line in tqdm(problems_to_process, desc="Evaluating Problems"):
                problem_data = json.loads(line)
                
                # Robustly get common fields
                quiz_json = problem_data.get('quiz')
                if not quiz_json: continue

                problem_id = problem_data.get('uuid')
                question = problem_data.get('problem')
                ground_truth_raw_str = str(problem_data.get('answer'))
                # IMPROVEMENT: Safer answer parsing
                ground_truth_answers_list = [ground_truth_raw_str]

                # Loop through the model portfolio
                for reasoner_config in REASONER_MODELS:
                    model_type = reasoner_config["type"]
                    num_traces = reasoner_config["num_traces"]
                    traces_to_evaluate = []
                    
                    if reasoner_config["source"] == "pre_generated":
                        # MODIFIED: Read from 'valid_reasoning_traces'
                        pre_gen_traces = problem_data.get('valid_reasoning_traces', [])[:num_traces]
                        for trace in pre_gen_traces:
                            traces_to_evaluate.append({"trace": trace, "model_id": f"pre_generated_{model_type}"})
                    
                    elif reasoner_config["source"] == "api_call":
                        for i in range(num_traces):
                            reasoner_prompt = REASONING_PROMPT.format(problem=question)
                            new_trace = call_llm_api(model_type, reasoner_prompt, reasoner_config["model_id"], reasoner_config["temperature"])
                            traces_to_evaluate.append({"trace": new_trace, "model_id": reasoner_config["model_id"]})
                            time.sleep(1)

                    # Evaluate each collected trace
                    for i, trace_info in enumerate(traces_to_evaluate):
                        reason_trace = trace_info["trace"]
                        if not reason_trace: continue # Skip if trace generation failed

                        extracted_answer = extract_boxed_answer(reason_trace)
                        is_correct = normalize_and_compare_answers(extracted_answer, ground_truth_answers_list)

                        grading_prompt = QUIZ_GRADING_PROMPT.format(
                            quiz_json_text=json.dumps(quiz_json, indent=2),
                            reasoner_trace_text=reason_trace
                        )
                        raw_grading_output = call_llm_api("grader", grading_prompt, GRADER_MODEL, 0.3)
                        grading_result = parse_json_from_text(raw_grading_output)
                        
                        reward_score = 0.0
                        if grading_result and "Score" in grading_result:
                            score_match = re.search(r'(\d+\.?\d*)', str(grading_result.get("Score")))
                            if score_match: reward_score = float(score_match.group(1))

                        result_record = {
                            "problem_id": problem_id, "generator_model": trace_info["model_id"],
                            "generator_type": model_type, "trace_num": i + 1, "is_correct": is_correct,
                            "extracted_answer": extracted_answer, "reward_score": reward_score,
                            "reason_trace": reason_trace, "grading_result": grading_result,
                        }
                        f_details.write(json.dumps(result_record) + '\n')
                        all_detailed_results.append(result_record)

    except KeyboardInterrupt:
        print("\n\nKEYBOARD INTERRUPT DETECTED! Stopping and proceeding to save overview...")
    
    # --- Final Analysis section, now reads from the in-memory list ---
    print("\n\n--- Generating Final Overview ---")
    
    if not all_detailed_results:
        print("No results were processed. Exiting.")
        return

    # (The rest of the analysis logic is perfect and requires no changes)
    total_traces = len(all_detailed_results)
    total_correct = sum(1 for r in all_detailed_results if r['is_correct'])
    accuracy = (total_correct / total_traces * 100) if total_traces > 0 else 0
    scores_when_correct = [r['reward_score'] for r in all_detailed_results if r['is_correct']]
    scores_when_incorrect = [r['reward_score'] for r in all_detailed_results if not r['is_correct']]
    avg_score_correct = sum(scores_when_correct) / len(scores_when_correct) if scores_when_correct else 0
    avg_score_incorrect = sum(scores_when_incorrect) / len(scores_when_incorrect) if scores_when_incorrect else 0
    
    overview_data = {
        "run_info": { "timestamp": RUN_TIMESTAMP, "input_file": INPUT_FILE, "reasoner_portfolio": REASONER_MODELS, "grader_model": GRADER_MODEL, "status": "Run Interrupted" if 'KeyboardInterrupt' in locals() else "Run Complete"},
        "overall_performance": { "problems_attempted": len(set(r['problem_id'] for r in all_detailed_results)), "traces_generated_and_saved": total_traces, "traces_correctly_answered": total_correct, "trace_accuracy_percent": round(accuracy, 2) },
        "correlation_analysis": { "average_reward_score_when_correct": round(avg_score_correct, 3), "average_reward_score_when_incorrect": round(avg_score_incorrect, 3), "comment": "This is the most important metric. A large positive gap proves the quiz score is a good proxy for correctness." }
    }

    with open(OUTPUT_OVERVIEW_FILE, 'w', encoding='utf-8') as f_overview:
        json.dump(overview_data, f_overview, indent=4)
        
    print(f"\n✅ Evaluation Complete (or Gracefully Stopped)!")
    print(f"  - Full details saved to: {OUTPUT_DETAILS_FILE}")
    print(f"  - Overview saved to: {OUTPUT_OVERVIEW_FILE}")
    print("\n--- Correlation Summary ---")
    print(f"Trace Accuracy: {accuracy:.2f}% ({total_correct}/{total_traces})")
    print(f"Avg. Reward Score (When Correct):   {avg_score_correct:.3f}")
    print(f"Avg. Reward Score (When Incorrect): {avg_score_incorrect:.3f}")

if __name__ == "__main__":
    run_full_evaluation()
