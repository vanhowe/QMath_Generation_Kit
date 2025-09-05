import json
import os
import re
import time
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
from prompts import QUIZ_GENERATION_PROMPT

# --- 需要老师改动Configuration ---
# IMPORTANT: Replace with your actual API key
COMMERCIAL_API_KEY = "YOUR_API_KEY_HERE" 
COMMERCIAL_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QUIZ_GENERATOR_MODEL = "deepseek-r1"

# --- 需要老师改动Script Behavior ---
# This script now reads a single .jsonl file and writes to another .jsonl file
INPUT_FILE = '/root/autodl-tmp/filtered_math_data_original_structure.jsonl' # 注意改写分块 00～04
OUTPUT_FILE = '/root/autodl-tmp/math_data_with_quizzes_number.jsonl' # 注意改写分块 00～04
CONCURRENT_REQUESTS = 50 # 同时发出api的次数

# --- API Client and Helper Functions (Unchanged) ---
client = OpenAI(api_key=COMMERCIAL_API_KEY, base_url=COMMERCIAL_API_URL, max_retries=2)

def call_llm_api(prompt, model_id, temperature=0.3):
    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=4096,
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

# --- MODIFIED: This function is now corrected to match your data structure ---
def process_single_problem(problem_data):
    output_record = problem_data.copy()
    
    # Gather reasoning text from both 'solution' and 'generations' fields
    reasoning_sources = []
    
    # 1. Get the solution if it's high-quality (e.g., longer than 100 chars)
    solution_text = problem_data.get('solution')
    if solution_text and isinstance(solution_text, str) and len(solution_text) > 100:
        reasoning_sources.append(solution_text)
        
    # 2. Get any high-quality generations
    generations = problem_data.get('generations', [])
    if generations and isinstance(generations, list):
        for gen_text in generations:
            if gen_text and isinstance(gen_text, str) and len(gen_text) > 100:
                reasoning_sources.append(gen_text)

    # If we found no good reasoning text anywhere, mark an error and return
    if not reasoning_sources:
        output_record["quiz"] = None
        output_record["error"] = "Record has no high-quality 'solution' or 'generations' to use."
        return output_record
    
    # Join the found traces into a single block of text for the prompt
    reasoning_text = "\n\n---\n\n".join(reasoning_sources)

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
        output_record.pop("error", None) # Remove error key on success
    else:
        output_record["quiz"] = None
        output_record["error"] = "Validation Error: Parsed JSON is valid, but missing 'quiz' key."
        output_record["received_json"] = quiz_json
    
    return output_record

# --- MODIFIED: Main function now processes the large file in memory-safe chunks ---
def generate_quizzes_from_jsonl():
    """
    Reads a large .jsonl file in chunks to avoid memory errors, generates quizzes,
    and saves the output to a new .jsonl file.
    """
    if not os.path.exists(INPUT_FILE):
        print(f"FATAL: Input file not found at '{INPUT_FILE}'. Please run the data preparation script first.")
        return

    # To get a total for the progress bar, we can count the lines first
    print("Counting total problems in input file...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        total_problems = sum(1 for line in f)
    
    print(f"Found {total_problems} problems to process.")

    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor, \
         open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        
        # We use executor.map on the file object directly. This creates a generator.
        # It reads one line, submits it to a worker thread, and moves to the next.
        # This is highly memory-efficient.
        problem_generator = (json.loads(line) for line in f_in)
        
        results_iterator = tqdm(
            executor.map(process_single_problem, problem_generator),
            total=total_problems,
            desc="Generating Quizzes"
        )
        
        # Write results to the output file as they are completed
        print(f"Writing results to {OUTPUT_FILE}...")
        for result in results_iterator:
            f_out.write(json.dumps(result) + '\n')

    print(f"\n✅ Finished processing. Output saved to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    generate_quizzes_from_jsonl()
