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

# 3. Run the Quiz Generation Script
This script will read the OpenR1-Math-220k dataset, select the best reasoning trace for each problem, and call an API to generate a 5-question quiz.

To run the script, open your terminal and execute:
```
python generate_quizzes.py
```
You can configure the number of problems to process and the number of concurrent API calls by editing the variables at the top of the generate_quizzes.py script.

Output: This will produce a file named OpenR1-Math_with_quizzes.jsonl.

# 4. Run the Trace Generation and Scoring Script
This script takes the output from the previous step and performs the main evaluation. For each problem, it will use a portfolio of models to generate new reasoning traces and then grade each one against the quiz.

To run the script, execute:
```
python generate_traces_and_grade.py
```
Output: This will produce two files:

run_details_{TIMESTAMP}.jsonl: A detailed log of every generated trace and its score.

run_overview_{TIMESTAMP}.json: A high-level summary of the run's performance.
