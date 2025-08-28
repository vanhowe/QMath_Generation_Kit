import json
import os
import re
import time
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
from prompts import QUIZ_GENERATION_PROMPT
import glob
import pandas as pd

# --- Configuration ---
COMMERCIAL_API_KEY = "YOUR_API_KEY_HERE" 
COMMERCIAL_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QUIZ_GENERATOR_MODEL = "deepseek-r1"

# --- Script Behavior ---
# This script reads from the 'processed' directory and writes to the 'with_quizzes' directory
INPUT_DIR = "data/processed/"
OUTPUT_DIR = "data/with_quizzes/"
CONCURRENT_REQUESTS = 50 # set higher to faster 

# --- API Client and Helper Functions ---
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

def process_single_problem(problem_data):
    # This worker function is largely unchanged, but now works with a dictionary
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

def generate_quizzes_in_chunks():
    """
    Finds all pre-processed data chunks, generates quizzes for each,
    and saves the output to corresponding new chunk files.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    input_chunk_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.parquet")))
    
    if not input_chunk_files:
        print(f"FATAL: No .parquet files found in '{INPUT_DIR}'. Please run 'prepare_dataset.py' first.")
        return

    print(f"Found {len(input_chunk_files)} data chunks to process.")

    for chunk_path in input_chunk_files:
        print(f"\n--- Processing Chunk: {chunk_path} ---")
        
        try:
            df = pd.read_parquet(chunk_path)
            # Convert DataFrame to list of dictionaries for processing
            problems_to_process = df.to_dict(orient='records')
        except Exception as e:
            print(f"  - Error reading chunk file: {e}. Skipping.")
            continue

        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
            results_iterator = tqdm(
                executor.map(process_single_problem, problems_to_process),
                total=len(problems_to_process),
                desc=f"Generating Quizzes for {os.path.basename(chunk_path)}"
            )
            
            # Convert results back to a DataFrame to save as Parquet
            results_list = list(results_iterator)
            output_df = pd.DataFrame(results_list)
            
            output_filename = os.path.join(OUTPUT_DIR, os.path.basename(chunk_path).replace('processed_numeric_data', 'data_with_quizzes'))
            output_df.to_parquet(output_filename, index=False)

        print(f"  - ✅ Finished processing chunk. Output saved to '{output_filename}'")

    print("\nAll quiz generation chunks have been processed successfully!")

if __name__ == "__main__":
    generate_quizzes_in_chunks()
