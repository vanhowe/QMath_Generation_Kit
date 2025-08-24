# --- Prompts ---

QUIZ_GENERATION_PROMPT = """
You are an expert mathematics educator with extensive experience in university-level curriculum design for fields including Algebra, Geometry, and Precalculus. Your task is to create a 5-question diagnostic quiz in a strict JSON format. This quiz is intended to precisely evaluate a student's strategic reasoning and procedural accuracy when solving the provided math problem.

The quiz must follow a specific pedagogical structure to deconstruct the student's problem-solving approach.

**Pedagogical Structure of the Quiz:**

The five questions must be structured to test the following stages of reasoning, in this specific order:

1.  **Question 1: The Conceptual Foundation.** This question MUST identify the core mathematical principle, theorem, or fundamental strategy required to even begin solving the problem correctly. (e.g., The Pythagorean Theorem, the formula for a circle's area, the concept of a system of equations).

2.  **Questions 2, 3, and 4: The Deconstruction Phase.** These questions MUST test three distinct, critical intermediate components or values that are calculated as part of the solution. They should be "path-agnostic" where possible, meaning they are necessary calculations regardless of minor variations in method.
    * *Examples:* Calculating the horizontal distance ($Δx$), the vertical distance ($Δy$), the value of a discriminant, a specific coefficient after an expansion, or the area of a sub-shape.
    * Each question must focus on a single, isolated calculation.

3.  **Question 5: The Synthesis Step.** This question MUST test the final assembly of the intermediate components into the final answer. It should verify the student's ability to correctly combine their previously calculated values using the proper formula or logic.
    * *Examples:* Correctly placing $Δx^2$ and $Δy^2$ into the distance formula to find the final radicand, substituting a solved variable back into an original equation, or combining the areas of sub-shapes.

**Content and Formatting Rules:**

* **Distractor Quality:** Incorrect options (distractors) must be plausible and derived from common procedural errors, such as sign mistakes, incorrect formula application, calculation errors, or misunderstanding the order of operations.
* **Randomization:** The position of the correct answer within the `options` array must be randomized for each question.

---

**JSON Output Requirements:**

You MUST generate a single, valid JSON object as your entire output. This object will contain one key, `"quiz"`, which holds an array of the 5 question objects. Adhere strictly to the schema below.

**JSON Schema and Example:**
```json
{{
  "quiz": [
    {{
      "question_id": 1,
      "question_text": "What is the primary mathematical strategy required to find the distance between the two points?",
      "options": [
        "Calculating the slope of the line",
        "Using the Pythagorean Theorem or Distance Formula",
        "Finding the midpoint of the segment",
        "Using trigonometric ratios"
      ],
      "correct_answer_index": 1,
      "reward_score": 0.2
    }},
    {{
      "question_id": 2,
      "question_text": "What is the correct value for the horizontal displacement (Δx) between the points (-4, 3) and (2, -6)?",
      "options": [
        "-2",
        "6",
        "2",
        "-6"
      ],
      "correct_answer_index": 1,
      "reward_score": 0.2
    }},
    {{
      "question_id": 3,
      "question_text": "What is the correct value for the vertical displacement (Δy) between the points (-4, 3) and (2, -6)?",
      "options": [
        "9",
        "3",
        "-3",
        "-9"
      ],
      "correct_answer_index": 3,
      "reward_score": 0.2
    }},
    {{
      "question_id": 4,
      "question_text": "What is the correct value for the squared vertical distance (Δy²)?",
      "options": [
        "9",
        "-81",
        "81",
        "-18"
      ],
      "correct_answer_index": 2,
      "reward_score": 0.2
    }},
    {{
      "question_id": 5,
      "question_text": "After calculating Δx² = 36 and Δy² = 81, what is the correct radicand (the value inside the square root) when these components are synthesized using the distance formula?",
      "options": [
        "45",
        "117",
        "9",
        "√15"
      ],
      "correct_answer_index": 1,
      "reward_score": 0.2
    }}
  ]
}}

IMPORTANT FINAL INSTRUCTION: Your entire response must be ONLY the JSON object, starting with {{ and ending with }}. Do not include any introductory text, explanations, design rationale, or any other text outside of the single JSON object.
Problem to Analyze:
{problem}

Gold-Standard Numeric Answer:
{answer}

Gold-Standard Human Reasoning:
{multiple_reason_solution}

"""

REASONING_PROMPT = """
**Objective:** Solve the following mathematical problem by producing a step-by-step reasoning trace.
**Instructions:**
1.  Analyze the problem to identify the goal.
2.  Formulate a clear plan.
3.  Execute your plan, showing all calculations.
4.  Conclude by placing the final numerical answer in a \\boxed{{}} block.
 **CRITICAL FORMATTING RULES FOR THE FINAL ANSWER:**
- The \\boxed{{}} block must contain ONLY the final answer.
- Do NOT include variable assignments (like "x = ...") inside the box.
- Do NOT include any explanatory text (like "\\text{{...}}") inside the box.
- For multiple-choice questions, provide only the numeric answer rather than the letter of the correct option (e.g., "81").

**--- Examples of CORRECT Final Answer Formatting ---**
- Correct: \\boxed{{1/4}}
- Correct: \\boxed{{10}}
- Correct: \\boxed{{-1, 7}}

**Problem:**
{problem}
"""

QUIZ_GRADING_PROMPT = """
**Objective:** Evaluate the provided "Reasoner Trace" against the "Quiz JSON" and provide a score.
**Instructions:**
1.  Read each question in the Quiz JSON.
2.  Find evidence in the Reasoner Trace to determine if the logic described in the correct option was followed.
3.  Your output MUST be a single, valid JSON object with NO other text. The JSON object must contain:
    - "Score": The total reward score summed from all correctly answered questions.
    - "Correct_Questions": A list of question numbers (integers) that were answered correctly.
    - "Wrong_Questions": A list of question numbers (integers) that were answered incorrectly.
    - "Reason_for_Failure": A brief explanation ONLY if the score is less than 1.0.

**Quiz JSON:**
{quiz_json_text}

**Reasoner Trace:**
{reasoner_trace_text}
"""
