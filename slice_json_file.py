import os
import sys
import math

def slice_jsonl_file():
    """
    Interactively prompts the user to slice a large JSONL file into a specified
    number of smaller, sequentially named files.
    """
    print("--- JSONL File Slicer ---")

    # 1. Get the input file from the user
    input_file = input("Enter the path to the JSONL file you want to slice: ").strip()

    if not os.path.exists(input_file):
        print(f"\nError: File not found at '{input_file}'")
        sys.exit(1)
        
    if not input_file.lower().endswith('.jsonl'):
        print(f"\nWarning: The file does not have a .jsonl extension. Proceeding anyway.")

    # 2. Get the number of slices from the user, with a default
    try:
        num_slices_str = input("Enter the number of slices to create (default is 4): ").strip()
        num_slices = int(num_slices_str) if num_slices_str else 4
        if num_slices <= 0:
            raise ValueError
    except ValueError:
        print("\nError: Please enter a valid positive number for the slices.")
        sys.exit(1)

    print("\nProcessing...")

    # 3. Count the total lines in the file efficiently
    print(f"-> Counting total lines in '{os.path.basename(input_file)}'...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)
        print(f"-> Found {total_lines} total lines (records).")
    except Exception as e:
        print(f"\nError: Could not read the file. Reason: {e}")
        sys.exit(1)

    if total_lines < num_slices:
        print(f"\nWarning: The file has fewer lines ({total_lines}) than the desired number of slices ({num_slices}).")
        print("         Each slice will have at most one line.")
        num_slices = total_lines

    if total_lines == 0:
        print("\nError: The input file is empty. Nothing to slice.")
        sys.exit(1)

    # 4. Calculate lines per slice and handle remainders
    lines_per_slice = total_lines // num_slices
    remainder = total_lines % num_slices
    print(f"-> Slicing into {num_slices} files with ~{lines_per_slice} lines each.")
    
    # 5. Get path components for naming the output files
    input_dir = os.path.dirname(input_file)
    base_name, extension = os.path.splitext(os.path.basename(input_file))
    
    # Determine padding width for sequential numbering (e.g., 01, 02 vs 1, 2)
    padding_width = len(str(num_slices - 1))

    # 6. Perform the slicing
    line_counter = 0
    with open(input_file, 'r', encoding='utf-8') as f_in:
        for i in range(num_slices):
            # Determine the exact number of lines for this specific slice
            num_lines_for_this_slice = lines_per_slice + (1 if i < remainder else 0)
            
            # Format the output file name
            slice_num_str = str(i).zfill(padding_width)
            total_slices_str = str(num_slices - 1).zfill(padding_width)
            output_filename = f"{base_name} {slice_num_str}-of-{total_slices_str}{extension}"
            output_path = os.path.join(input_dir, output_filename)
            
            print(f"-> Creating '{output_filename}'...")
            
            with open(output_path, 'w', encoding='utf-8') as f_out:
                for _ in range(num_lines_for_this_slice):
                    line = f_in.readline()
                    if not line:
                        break # Stop if we unexpectedly reach the end of the input file
                    f_out.write(line)
                    line_counter += 1

    print("\n-------------------------")
    print(f"✅ Slicing Complete!")
    print(f"   - Total lines processed: {line_counter}")
    print(f"   - Number of files created: {num_slices}")
    print(f"   - Output files are located in: {input_dir or '.'}")
    print("-------------------------")

if __name__ == "__main__":
    slice_jsonl_file()
```

### How to Use the Script

1.  **Save the file:** Save the code above into a file named `slice_jsonl.py` in your project directory.
2.  **Run from the terminal:**
    ```bash
    python slice_jsonl.py
    
