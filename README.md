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

run_details_{TIMESTAMP}.jsonl: A detailed log of every generated trace and its score.
run_overview_{TIMESTAMP}.json: A high-level summary of the run's performance.

Output: This will produce a final file named data_with_quizzes.jsonl, which contains the fully augmented dataset.

