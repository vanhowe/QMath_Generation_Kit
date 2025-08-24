import json
import os
import re
import time
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
from prompts import QUIZ_GENERATION_PROMPT

# --- Configuration ---
# API credentials (MUST BE FILLED IN BY THE USER)
COMMERCIAL_API_KEY = "YOUR_API_KEY_HERE" 
COMMERCIAL_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1" # Or your endpoint
QUIZ_GENERATOR_MODEL = "deepseek-r1" # Or another powerful model

# --- Script Behavior ---
# This script reads the output from 'prepare_dataset.py'
INPUT_FILE = "preprocessed_numeric_data.jsonl"
OUTPUT_FILE = "data_with_quizzes.jsonl"

# Concurrency settings
CONCURRENT_REQUESTS = 10   # Number of parallel API calls

# --- API Client and Helper Functions ---
client = OpenAI(api_key=COMMERCIAL_API_KEY, base_url=COMMERCIAL_API_URL, max_retries=2)

def call_llm_api(prompt, model_id, temperature=0.3):
    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2048,
            timeout=400.0,
        )
        return completion.choices[0].message.content, None
    except Exception as e:
        return None, f"API Error: {e}"

def parse_json_from_text(text_blob: str):
    if not text_blob:
        return None, "No content received from API."
    match = re.search(r'\{.*\}', text_blob, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0)), None
        except json.JSONDecodeError as e:
            return None, f"JSON Decode Error: {e}"
    return None, "No JSON object found in response."

def process_single_problem(problem_data):
    """Processes a single, pre-cleaned problem to generate a quiz."""
    output_record = problem_data.copy()
    
    reasoning_text = problem_data.get('gold_standard_reasoning')
    if not reasoning_text:
        output_record["quiz"] = None
        output_record["error"] = "Input record was missing 'gold_standard_reasoning'."
        return output_record

    quiz_gen_prompt = QUIZ_GENERATION_PROMPT.format(
        problem=problem_data.get('problem', 'N/A'),
        answer=problem_data.get('answer', 'N/A'),
        multiple_reason_solution=reasoning_text
    )

    raw_quiz_output, api_error = call_llm_api(quiz_gen_prompt, QUIZ_GENERATOR_MODEL)
    if api_error:
        output_record["quiz"] = None
        output_record["error"] = api_error
        return output_record

    quiz_json, parsing_error = parse_json_from_text(raw_quiz_output)
    if parsing_error:
        output_record["quiz"] = None
        output_record["error"] = parsing_error
        output_record["failed_raw_output"] = raw_quiz_output
        return output_record

    if "quiz" in quiz_json:
        output_record["quiz"] = quiz_json["quiz"]
    else:
        output_record["quiz"] = None
        output_record["error"] = "Validation Error: Parsed JSON is valid, but missing 'quiz' key."
        output_record["received_json"] = quiz_json
    
    return output_record

def generate_quizzes():
    print(f"Loading pre-processed data from '{INPUT_FILE}'...")
    try:
        problems_to_process = []
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                problems_to_process.append(json.loads(line))
    except FileNotFoundError:
        print(f"FATAL: Input file not found at '{INPUT_FILE}'. Please run 'prepare_dataset.py' first.")
        return
    except Exception as e:
        print(f"FATAL: Could not load dataset. Error: {e}")
        return

    print(f"Starting quiz generation for {len(problems_to_process)} problems with CONCURRENT_REQUESTS = {CONCURRENT_REQUESTS}")

    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        
        results_iterator = tqdm(
            executor.map(process_single_problem, problems_to_process),
            total=len(problems_to_process),
            desc="Generating Quizzes"
        )
        
        for record in results_iterator:
            f_out.write(json.dumps(record) + '\n')

    print(f"\n✅ Quiz generation complete!")
    print(f"Output saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_quizzes()
