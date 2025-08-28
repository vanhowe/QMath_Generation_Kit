import json
import os
import re
import time
from tqdm import tqdm
from datetime import datetime
from openai import OpenAI
from prompts import REASONING_PROMPT, QUIZ_GRADING_PROMPT
import glob
import pandas as pd

# --- Configuration ---

# -- API Endpoints & Keys (Collaborator MUST configure this section) --

GRADER_API_URL = "DEEPSEEK V3 API HERE"
GRADER_API_KEY = "YOUR_COMMERCIAL_API_KEY_HERE" 
GRADER_MODEL = "deepseek-v3" # The model identifier for the DeepSeek API


LOCAL_API_URL_PEER = "http://localhost:8000/v1"
LOCAL_API_KEY_PEER = "EMPTY"

LOCAL_API_URL_STUDENT = "http://localhost:8001/v1"
LOCAL_API_KEY_STUDENT = "EMPTY"

# --- Portfolio of Reasoner Models ---
REASONER_MODELS = [
    {
        "type": "expert",
        "source": "pre_generated",
        "num_traces": 2
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

# -- File I/O & Script Behavior --
NPUT_DIR = "data/with_quizzes/"
OUTPUT_DETAILS_DIR = "results/details/"
OUTPUT_OVERVIEW_DIR = "results/overview/"

RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_OVERVIEW_FILE = os.path.join(OUTPUT_OVERVIEW_DIR, f"run_overview_{RUN_TIMESTAMP}.json")

# --- Helper Functions ---
def call_llm_api(prompt, model_id, temperature, api_url, api_key):
    """Calls an OpenAI-compatible API using specific credentials for each call."""
    try:
        client = OpenAI(api_key=api_key, base_url=api_url, max_retries=2)
        completion = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2048,
            timeout=300.0,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"    API Error calling {model_id} at {api_url}: {e}")
        return None

def extract_boxed_answer(trace_text):
    """Parses a string to find the content within \\boxed{...} using a non-greedy match."""
    if not trace_text: return None
    match = re.search(r"\\boxed\{(.*?)\}", trace_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def parse_json_from_text(text):
    """Extracts a JSON object from a string."""
    if not text: return None
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None

def normalize_and_compare_answers(extracted_answer_raw, ground_truth_answers_list):
    """Compares one extracted answer against a list of possible ground-truth answers."""
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
    os.makedirs(OUTPUT_DETAILS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_OVERVIEW_DIR, exist_ok=True)
    
    input_chunk_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.parquet")))
    if not input_chunk_files:
        print(f"FATAL: No .parquet files found in '{INPUT_DIR}'. Please run 'generate_quizzes.py' first.")
        return

    print(f"Found {len(input_chunk_files)} data chunks with quizzes to process.")
    
    # This list will track the filenames of the result chunks we create.
    newly_created_detail_files = []

    try:
        for chunk_path in input_chunk_files:
            print(f"\n--- Processing Chunk: {chunk_path} ---")
            
            try:
                df = pd.read_parquet(chunk_path)
                problems_to_process = df.to_dict(orient='records')
            except Exception as e:
                print(f"  - Error reading chunk file: {e}. Skipping.")
                continue

            # Define a unique output filename for this chunk's results
            output_filename = os.path.join(OUTPUT_DETAILS_DIR, f"run_details_{RUN_TIMESTAMP}_{os.path.basename(chunk_path)}")
            newly_created_detail_files.append(output_filename)

            with open(output_filename, 'w', encoding='utf-8') as f_details:
                for problem_data in tqdm(problems_to_process, desc=f"Evaluating {os.path.basename(chunk_path)}"):
                    # Robustly get common fields from the problem data
                    problem_id = problem_data.get('uuid')
                    question = problem_data.get('problem')
                    ground_truth_raw_str = str(problem_data.get('answer'))
                    ground_truth_answers_list = [ans.strip() for ans in re.split(r'\s+or\s+|\s*,\s*|\s*;\s*', ground_truth_raw_str)]
                    quiz_json = problem_data.get('quiz')

                    if not quiz_json:
                        continue

                    # Loop through the model portfolio to get/generate traces
                    for reasoner_config in REASONER_MODELS:
                        model_type = reasoner_config["type"]
                        num_traces = reasoner_config["num_traces"]
                        traces_to_evaluate = []
                        
                        if reasoner_config["source"] == "pre_generated":
                            pre_gen_traces = problem_data.get('generations', [])[:num_traces]
                            for trace in pre_gen_traces:
                                traces_to_evaluate.append({
                                    "trace": trace, 
                                    "model_id": f"pre_generated_{model_type}"
                                })
                        elif reasoner_config["source"] == "api_call":
                            model_id = reasoner_config["model_id"]
                            temperature = reasoner_config["temperature"]
                            api_url = reasoner_config["api_url"]
                            api_key = reasoner_config["api_key"]
                            
                            for i in range(num_traces):
                                reasoner_prompt = REASONING_PROMPT.format(problem=question)
                                new_trace = call_llm_api(reasoner_prompt, model_id, temperature, api_url, api_key)
                                traces_to_evaluate.append({"trace": new_trace, "model_id": model_id})
                                time.sleep(1)

                        # Evaluate each collected trace
                        for i, trace_info in enumerate(traces_to_evaluate):
                            reason_trace = trace_info["trace"]
                            generator_model = trace_info["model_id"]
                            
                            extracted_answer = extract_boxed_answer(reason_trace)
                            is_correct = normalize_and_compare_answers(extracted_answer, ground_truth_answers_list)

                            grading_prompt = QUIZ_GRADING_PROMPT.format(
                                quiz_json_text=json.dumps(quiz_json, indent=2),
                                reasoner_trace_text=reason_trace
                            )
                            raw_grading_output = call_llm_api(grading_prompt, GRADER_MODEL, 0.3, GRADER_API_URL, GRADER_API_KEY)
                            grading_result = parse_json_from_text(raw_grading_output)
                            
                            reward_score = 0.0
                            if grading_result and "Score" in grading_result:
                                score_match = re.search(r'(\d+\.?\d*)', str(grading_result.get("Score")))
                                if score_match:
                                    reward_score = float(score_match.group(1))

                            result_record = {
                                "problem_id": problem_id, "question": question, "ground_truth_answer": ground_truth_raw_str,
                                "generator_model": generator_model, "generator_type": model_type, "trace_num": i + 1,
                                "is_correct": is_correct, "extracted_answer": extracted_answer,
                                "reward_score": reward_score, "reason_trace": reason_trace, "grading_result": grading_result,
                            }
                            f_details.write(json.dumps(result_record) + '\n')

    except KeyboardInterrupt:
        print("\n\nKEYBOARD INTERRUPT DETECTED! Stopping and proceeding to save overview...")
    
    # --- This is the complete Final Analysis section you provided ---
    print("\n\n--- Generating Final Overview from All Processed Chunks ---")
    
    all_detailed_results = []
    # Read from the files we just created in this run
    for detail_file in newly_created_detail_files:
        if os.path.exists(detail_file):
            with open(detail_file, 'r', encoding='utf-8') as f:
                for line in f:
                    all_detailed_results.append(json.loads(line))

    if not all_detailed_results:
        print("No results were processed. Exiting.")
        return

    total_traces = len(all_detailed_results)
    total_correct = sum(1 for r in all_detailed_results if r['is_correct'])
    accuracy = (total_correct / total_traces * 100) if total_traces > 0 else 0
    
    scores_when_correct = [r['reward_score'] for r in all_detailed_results if r['is_correct']]
    scores_when_incorrect = [r['reward_score'] for r in all_detailed_results if not r['is_correct']]
    avg_score_correct = sum(scores_when_correct) / len(scores_when_correct) if scores_when_correct else 0
    avg_score_incorrect = sum(scores_when_incorrect) / len(scores_when_incorrect) if scores_when_incorrect else 0
    
    overview_data = {
        "run_info": { 
            "timestamp": RUN_TIMESTAMP, 
            "input_directory": INPUT_DIR, 
            "reasoner_portfolio": REASONER_MODELS, 
            "grader_model": GRADER_MODEL,
            "status": "Run Interrupted" if 'KeyboardInterrupt' in locals() else "Run Complete"
        },
        "overall_performance": { 
            "problems_attempted": len(set(r['problem_id'] for r in all_detailed_results)),
            "traces_generated_and_saved": total_traces, 
            "traces_correctly_answered": total_correct, 
            "trace_accuracy_percent": round(accuracy, 2) 
        },
        "correlation_analysis": { 
            "average_reward_score_when_correct": round(avg_score_correct, 3), 
            "average_reward_score_when_incorrect": round(avg_score_incorrect, 3), 
            "comment": "This is the most important metric. A large positive gap proves the quiz score is a good proxy for correctness." 
        }
    }

    with open(OUTPUT_OVERVIEW_FILE, 'w', encoding='utf-8') as f_overview:
        json.dump(overview_data, f_overview, indent=4)
        
    print(f"\n✅ Evaluation Complete (or Gracefully Stopped)!")
    print(f"  - Full details saved to chunks in: {OUTPUT_DETAILS_DIR}")
    print(f"  - Overview saved to: {OUTPUT_OVERVIEW_FILE}")
    print("\n--- Correlation Summary ---")
    print(f"Trace Accuracy: {accuracy:.2f}% ({total_correct}/{total_traces})")
    print(f"Avg. Reward Score (When Correct):   {avg_score_correct:.3f}")
    print(f"Avg. Reward Score (When Incorrect): {avg_score_incorrect:.3f}")

if __name__ == "__main__":
    run_full_evaluation()
