import json
import re
from tqdm import tqdm
from datasets import load_dataset
import os

# --- Configuration ---
# The Hugging Face dataset to download
HF_DATASET_ID = "open-r1/OpenR1-Math-220k"
HF_DATASET_SPLIT = "default"

# How many problems to process from the raw dataset.
# Set to None to process the entire dataset.
PROBLEMS_TO_PROCESS = None


# The clean, filtered output file that will be used by the next script
OUTPUT_FILE = "preprocessed_numeric_data.jsonl"

# --- Helper Function to Filter for Numeric Answers ---
def is_purely_numeric(answer_str: str) -> bool:
    """
    Determines if an answer string is "purely numeric".
    Returns True if the string can be converted to a float and contains no complex syntax.
    Returns False for everything else, INCLUDING MCQ letters.
    """
    if not isinstance(answer_str, str):
        answer_str = str(answer_str)
    
    s = answer_str.strip()
    
    if not s:
        return False
        
    # Reject anything that contains obvious non-numeric syntax
    if '\\' in s or '{' in s or '}' in s or '_' in s or '^' in s:
        return False
    
    if 'or' in s.lower() or ',' in s or ';' in s:
        return False

    # If it contains any letters, it's not purely numeric.
    if any(c.isalpha() for c in s):
        return False
    
    # Finally, try to convert it to a number.
    try:
        float(s)
        return True
    except ValueError:
        return False

# --- Main Pre-processing Logic ---
def prepare_dataset():
    """
    Downloads the full dataset to a local cache first, then filters for
    numeric-only answers and saves to a clean JSONL file.
    """
    print(f"--- Starting Data Preparation ---")
    print(f"Downloading dataset '{HF_DATASET_ID}' from Hugging Face. This may take a while...")
    try:
        # --- MODIFIED: Removed streaming=True for a more robust download ---
        ds = load_dataset(HF_DATASET_ID, HF_DATASET_SPLIT, split='train')
        
        if PROBLEMS_TO_PROCESS:
            ds = ds.select(range(PROBLEMS_TO_PROCESS))
        print(f"Successfully downloaded and loaded {len(ds)} problems.")

    except Exception as e:
        print(f"FATAL: Could not load dataset. Ensure you are logged in with 'huggingface-cli login'. Error: {e}")
        return

    processed_records = []
    
    print("Filtering for numeric answers and selecting best reasoning trace...")
    for problem_data in tqdm(ds, desc="Pre-processing Problems"):
        ground_truth_answer = problem_data.get('answer')
        
        # --- Step 1: Filter for purely numeric answers ---
        if not is_purely_numeric(ground_truth_answer):
            continue # Skip this problem

        # --- Step 2: Intelligently select the best reasoning text ---
        best_reasoning_text = None
        reasoning_source = "unknown"
        
        generations = problem_data.get('generations', [])
        correctness_flags = problem_data.get('correctness_math_verify', [])
        
        if generations and correctness_flags and len(generations) == len(correctness_flags):
            for i, is_correct in enumerate(correctness_flags):
                if is_correct and isinstance(generations[i], str) and len(generations[i]) > 100:
                    best_reasoning_text = generations[i]
                    reasoning_source = f"generation_{i}_verified_correct"
                    break
        
        if not best_reasoning_text and generations and isinstance(generations[0], str) and len(generations[0]) > 100:
            best_reasoning_text = generations[0]
            reasoning_source = "generation_0_unverified"

        if not best_reasoning_text:
            best_reasoning_text = problem_data.get('solution', '')
            reasoning_source = "solution_field"

        # --- Step 3: Create a clean, standardized record ---
        clean_record = {
            "uuid": problem_data.get('uuid'),
            "problem": problem_data.get('problem'),
            "answer": str(ground_truth_answer),
            "gold_standard_reasoning": best_reasoning_text,
            "reasoning_source": reasoning_source
        }
        processed_records.append(clean_record)

    # --- Step 4: Write all the clean records to the output file ---
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        for record in processed_records:
            f_out.write(json.dumps(record) + '\n')
            
    print(f"\n✅ Pre-processing complete.")
    print(f"  - Total problems read: {len(ds)}")
    print(f"  - Problems with numeric answers kept: {len(processed_records)}")
    print(f"  - Clean data saved to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    prepare_dataset()
