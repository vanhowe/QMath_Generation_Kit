## QMath Generation Kit - Collaborator Guide
# 1. Project Overview
Welcome to the QMath project! This repository contains a suite of scripts to build a high-quality dataset for training mathematical reasoning models. The pipeline is designed to be run by a collaborator with access to a local GPU cluster.

Important Note on Large Datasets: This pipeline is designed to handle very large datasets by processing them as a series of individual .parquet files. This file-based chunking keeps memory usage low and makes the entire process robust and resumable.

The workflow is broken down into a clear directory structure and a series of scripts that must be run in order.

Directory Structure
Before you begin, ensure your repository has the following directory structure. You will need to create these folders.
```
QMath-Generation-Kit/
├── data/
│   ├── raw/              <-- Place downloaded .parquet files here
│   ├── processed/        <-- Script 1 (prepare) output goes here
│   └── with_quizzes/     <-- Script 2 (quiz gen) output goes here
├── results/
│   ├── details/          <-- Script 3 (trace gen) output chunks go here
│   └── overview/         <-- Script 3 summary goes here
├── prepare_dataset.py      # Script 1
├── generate_quizzes.py     # Script 2
├── generate_traces_and_grade.py # Script 3
├── deploy_local_models.sh
...

```

# 2. The Full 5-Step Workflow
Step 1: Initial Setup
This step only needs to be done once.

A. Download the Data:
Manually download the open-r1/OpenR1-Math-220k dataset files. Place all the .parquet files (e.g., 0000.parquet, 0001.parquet, etc.) into the data/raw/ directory.

B. Create a Python Environment:
```
python -m venv qmath_env
source qmath_env/bin/activate
pip install -r requirements.txt
```
Step 2: Prepare and Chunk the Dataset
This script finds all raw Parquet files in data/raw/, filters them for problems with purely numeric answers, and saves the clean, standardized output into new chunk files in the data/processed/ directory.

Run the script:
```
python prepare_dataset.py
```
Step 3: Generate Quizzes for Each Chunk
This script finds all the processed chunks from the previous step and generates a diagnostic quiz for each problem, saving the augmented chunks to data/with_quizzes/.

A. Configure your API Key:
Open generate_quizzes.py and fill in your commercial API key.

B. Run the script:
```
python generate_quizzes.py
```
Step 4: Generate and Score Traces
This is the main data generation phase. It will process each quiz chunk sequentially.

A. Deploy Local Models:
Use the provided script to launch the local "peer" and "student" models on your cluster.
```
chmod +x deploy_local_models.sh
./deploy_local_models.sh
```
B. Configure the Evaluation Script:
Open generate_traces_and_grade.py, fill in your GRADER_API_KEY, and ensure the local API URLs are correct.

C. Run the script:
```
python generate_traces_and_grade.py
```
This will read from data/with_quizzes/ and save result chunks to results/details/.

Step 5: Merge and Upload Your Final Results (optional)
A. Merge the Result Chunks:
Combine all the detailed log chunks into a single file.
```
python merge_results.py
```
This creates final_merged_run_details.jsonl.

B. Upload the Final Files:
Use the aliyunpan-cli tool to upload the final merged details file and the final overview report.

# Log in if you haven't already
```
aliyunpan login --refresh-token <YOUR_REFRESH_TOKEN_HERE>
```
# Upload your two output files
```
aliyunpan upload final_merged_run_details.jsonl QMath_Runs/
aliyunpan upload run_overview_*.json QMath_Runs/
```
C. Share the Folder Link:
Create a share link for the QMath_Runs folder and send it to the primary researcher.

Thank you for your contribution to the QMath project!
