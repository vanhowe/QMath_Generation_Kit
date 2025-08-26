# QMath_Generation_Kit
QMath Generation Kit
This repository contains the scripts and prompts necessary to perform two key tasks for the QMath research project:

Quiz Generation: Augmenting a math problem dataset with diagnostic quizzes.

Trace Generation & Scoring: Generating multiple reasoning traces for each problem and scoring them against the generated quiz.

Step-by-Step Instructions

# 1. Setup Your Environment
First, you need to set up a Python environment and install the required libraries.

# Create a new virtual environment (recommended)
```
python -m venv qmath_env
source qmath_env/bin/activate
```

# Install the necessary libraries
```
pip install -r requirements.txt
```

You will also need to log in to your Hugging Face account to download the dataset. If you haven't already, run this command and enter your token:
```
huggingface-cli login
```

# 2. Configure Your API Credentials
Both scripts require an API key to function. Open the generate_quizzes.py and generate_traces_and_grade.py files and locate the configuration section at the top. You must replace the placeholder API key with your own.

# In both .py files, find this section:
```
COMMERCIAL_API_KEY = "YOUR_API_KEY_HERE" 
COMMERCIAL_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1" # Or your endpoint
```
# 3. Run the Data Preparation Script
This is the first step. This script will download the OpenR1-Math-220k dataset, filter it to keep only problems with purely numeric answers, and select the best reasoning trace for each problem.

To run the script, open your terminal and execute:
```
python prepare_dataset.py
```
Output: This will produce a file named preprocessed_numeric_data.jsonl. This file is the input for the next step.

# 4. Run the Quiz Generation Script
After the data preparation is complete, you can generate the quizzes. This script reads the clean preprocessed_numeric_data.jsonl file and calls an API to generate a 5-question quiz for each entry.

To run the script, execute:
```
python generate_quizzes.py
```
Output: This will produce a final file named data_with_quizzes.jsonl, which contains the fully augmented dataset.

# 5: Run the generate_traces_and_grade.py Script
```
generate_traces_and_grade.py
```


Output: This will produce two files:
```
run_details_{TIMESTAMP}.jsonl: A detailed log of every generated trace and its score.
run_overview_{TIMESTAMP}.json: A high-level summary of the run's performance.
```
Output: This will produce a final file named data_with_quizzes.jsonl, which contains the fully augmented dataset.

# Uploading Results
This guide provides the final step for collaborators after successfully running the data generation scripts. The following instructions detail how to upload your results to a shared Aliyun Pan (阿里云盘) folder so the primary researcher can access them for analysis and publication.

We will use an open-source command-line tool called aliyunpan-cli.

# Step 1: Install the Aliyun Pan Uploader
First, you need to install the command-line tool. If you are still in the same Python virtual environment (qmath_env), you can install it directly.

Open your terminal and run:
```
pip install aliyunpan
```
# Step 2: Log In to Your Aliyun Pan Account
The tool needs to be linked to an Aliyun Pan account. The first time you use it, you will need to log in.

Run the login command:
```
aliyunpan login
```
The tool will display a QR code in your terminal. Use the Aliyun Pan mobile app to scan this QR code to authorize the command-line tool.

# Step 3: Create a Designated Upload Folder
To keep our research data organized, please create a specific folder in your Aliyun Pan drive.

Run the "make directory" command to create a folder named QMath_Runs:
```
aliyunpan mkdir QMath_Runs
```
If the folder already exists, this command will safely do nothing.

# Step 4: Upload Your Generated Files
After you have successfully run the generate_traces_and_grade.py script, you will have two output files in your directory with a unique timestamp, for example:

run_details_20250819_043000.jsonl

run_overview_20250819_043000.json

You can upload both of these files to the QMath_Runs folder you just created.

Navigate to your QMath-Generation-Kit directory in the terminal.

Run the following two commands. The * wildcard will automatically find the correct timestamped files.

# Upload the detailed results log
```
aliyunpan upload run_details_*.jsonl QMath_Runs/
```
# Upload the summary report
```
aliyunpan upload run_overview_*.json QMath_Runs/
```
You will see a progress bar as the files are uploaded.

# Step 5: Share the Folder Link
Once the uploads are complete, the final step is to share the results.

Go to your Aliyun Pan account in your web browser or mobile app.

Find the QMath_Runs folder.

Create a share link for the entire folder.

Send this link to the primary researcher.

Thank you for your contribution to the QMath project!
