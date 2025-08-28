#!/bin/bash
# This script launches the two required open-source reasoner models on local servers
# using the vLLM library. Each model will run on a different port.
#
# Prerequisites:
# 1. vLLM must be installed (`pip install vllm`).
# 2. You must have sufficient GPU memory to host both models.
#
# Instructions:
# 1. Open your terminal.
# 2. Make this script executable: `chmod +x deploy_local_models.sh`
# 3. Run the script: `./deploy_local_models.sh`
#
# Two server processes will start in the background. You can close the terminal
# and they will continue running. To stop them, you will need to find and

# kill the corresponding processes.

echo "--- Starting QMath Local Model Deployment ---"

# --- Launch Peer Model (Qwen2.5-72B-Instruct) on Port 8000 ---
echo "Launching Peer model (Qwen/Qwen2.5-72B-Instruct) on http://localhost:8000 ..."
nohup python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-72B-Instruct \
    --port 8000 \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.9 \
    > peer_model_server.log 2>&1 &

PEER_PID=$!
echo "Peer model server started with PID: $PEER_PID. Logs are in peer_model_server.log"
sleep 10 # Give the first server a moment to start up

# --- Launch Student Model (Qwen2.5-7B-Instruct) on Port 8001 ---
echo "Launching Student model (Qwen/Qwen2.5-7B-Instruct) on http://localhost:8001 ..."
nohup python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --port 8001 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.9 \
    > student_model_server.log 2>&1 &

STUDENT_PID=$!
echo "Student model server started with PID: $STUDENT_PID. Logs are in student_model_server.log"

echo ""
echo "✅ Both model servers have been launched in the background."
echo "You can now run the main 'generate_traces_and_grade.py' script."
echo "To stop the servers, use the command: 'kill $PEER_PID $STUDENT_PID'"

