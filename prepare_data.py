import json
import os
from tqdm import tqdm
from datasets import load_dataset

# --- Configuration ---
HF_DATASET_ID = "open-r1/OpenR1-Math-220k"
HF_DATASET_SPLIT = "default"
PROBLEMS_TO_PROCESS = None # Set to an integer for testing, None for full dataset

BASE_DIR = "/root/autodl-tmp"
HF_CACHE_DIR = os.path.join(BASE_DIR, "huggingface_cache")

# --- MODIFIED: Define two output files ---
# 1. This file will contain ALL high-quality records, same as before.
OUTPUT_FILE_ALL = os.path.join(BASE_DIR, "open_r1_math_data_original.jsonl")
# 2. This NEW file will contain only the subset with simple numeric answers.
OUTPUT_FILE_NUMERIC = os.path.join(BASE_DIR, "open_r1_math_data_numeric_only.jsonl")


# --- NEW: Helper function to check for simple integer answers ---
def is_simple_numeric_answer(answer_str: str) -> bool:
    """
    Checks if an answer string represents a simple integer (e.g., "8", "-27").
    Returns False for decimals, fractions, letters, or complex formats.
    """
    if not isinstance(answer_str, str):
        return False
    
    try:
        # Strip whitespace and try to convert to an integer.
        # This will fail for floats ("3.14"), fractions ("5/13"), and letters ("D").
        int(answer_str.strip())
        return True
    except ValueError:
        return False


# --- Main Pre-processing Logic ---
def prepare_dataset():
    """
    Downloads the dataset, filters for high-quality records, and saves two files:
    1. All high-quality records, preserving their original structure.
    2. A subset of (1) containing only problems with simple integer answers.
    """
    print(f"--- Starting Data Preparation (Dual Output) ---")
    os.makedirs(HF_CACHE_DIR, exist_ok=True)
    
    print(f"Downloading dataset '{HF_DATASET_ID}' to cache: {HF_CACHE_DIR}")
    try:
        ds = load_dataset(HF_DATASET_ID, HF_DATASET_SPLIT, split='train', cache_dir=HF_CACHE_DIR)
        if PROBLEMS_TO_PROCESS:
            ds = ds.select(range(PROBLEMS_TO_PROCESS))
        total_problems_to_process = len(ds)
        print(f"Successfully downloaded and loaded {total_problems_to_process} problems.")

    except Exception as e:
        print(f"FATAL: Could not load dataset. Error: {e}")
        return

    # --- MODIFIED: Two counters for two output files ---
    records_written_all = 0
    records_written_numeric = 0
    
    print(f"Filtering records and writing to two files:")
    print(f"  - All high-quality records: {OUTPUT_FILE_ALL}")
    print(f"  - Numeric-only subset:      {OUTPUT_FILE_NUMERIC}")

    # --- MODIFIED: Open both files for writing ---
    with open(OUTPUT_FILE_ALL, 'w', encoding='utf-8') as f_all, \
         open(OUTPUT_FILE_NUMERIC, 'w', encoding='utf-8') as f_numeric:
        
        for problem_data in tqdm(ds, desc="Filtering Problems"):
            
            # Stage 1: "Gatekeeper" logic for overall quality (unchanged)
            is_record_valid = False

            solution_text = problem_data.get('solution')
            if solution_text and isinstance(solution_text, str) and len(solution_text) > 100:
                is_record_valid = True

            if not is_record_valid:
                generations = problem_data.get('generations', [])
                correctness_flags = problem_data.get('correctness_math_verify', [])
                
                if generations and correctness_flags and len(generations) == len(correctness_flags):
                    for i, is_correct in enumerate(correctness_flags):
                        if is_correct:
                            generation_text = generations[i]
                            if isinstance(generation_text, str) and len(generation_text) > 100:
                                is_record_valid = True
                                break

            # If the record is not high-quality, skip it entirely.
            if not is_record_valid:
                continue
            
            # --- Stage 2: Write to files based on the new filter ---
            
            # Prepare the record for writing (same as before)
            output_record = problem_data.copy()
            output_record.pop('messages', None)
            record_as_json_string = json.dumps(output_record) + '\n'

            # Action 1: Every valid, high-quality record gets written to the main file.
            f_all.write(record_as_json_string)
            records_written_all += 1
            
            # Action 2: Apply the new numeric filter.
            answer = problem_data.get('answer')
            if is_simple_numeric_answer(answer):
                # If it passes, also write it to the numeric-only subset file.
                f_numeric.write(record_as_json_string)
                records_written_numeric += 1
            
    print(f"\n✅ Filtering complete.")
    print(f"  - Total problems read: {total_problems_to_process}")
    print(f"  - Total high-quality records saved to '{os.path.basename(OUTPUT_FILE_ALL)}': {records_written_all}")
    print(f"  - Numeric-only records saved to '{os.path.basename(OUTPUT_FILE_NUMERIC)}': {records_written_numeric}")

if __name__ == "__main__":
    prepare_dataset()
