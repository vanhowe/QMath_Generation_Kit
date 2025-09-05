# QMath 数据处理与评估流程指南
📌 概述
本指南详细说明了从原始数据到最终评估结果的完整流程，包括数据预处理、测验生成、推理轨迹生成与评分等关键步骤。流程设计为模块化执行，支持分块处理以提高效率。

### 步骤1：预处理数据
目标：从原始数据中提取纯数字答案的问题，生成标准化数据集

### 1. 登录 Hugging Face（仅首次需要）
```
huggingface-cli login  # 输入您的 Hugging Face Token
```
### 2. 运行预处理脚本
```
python prepare_data.py
```

输出文件
data/processed/open_r1_math_data_original.jsonl	     原始中间数据	调试用（不参与后续流程）
data/processed/open_r1_math_data_numeric_only.jsonl	     纯数字答案过滤后数据	核心输入文件（必须使用）
⚠️ 重要说明：

仅 numeric_only 文件包含有效数据（过滤非数字答案问题）
原始文件仅用于调试，切勿在后续步骤中使用

### 步骤1.5：数据切分（关键新增步骤）
目标：将大文件分割为小块，避免后续处理内存溢出

### 运行切分脚本（必须在 prepare_data.py 后执行）
```
python slice_jsonl.py
```
📂 输入/输出
输入	data/processed/open_r1_math_data_numeric_only.jsonl	步骤1生成的过滤后数据
输出	data/sliced/slice_{0..3}.jsonl	4个等分小文件（每块约25%数据）

⚠️ 执行顺序警告：
必须在 prepare_data.py 之后、generate_quizzes.py 之前运行！
未切分数据将导致后续步骤内存崩溃

### 步骤2：生成诊断测验
目标：为每个数学问题生成诊断性测验（含错误选项）

🔑 配置步骤
编辑 generate_quizzes.py：
### 🚀 执行命令
'''
python generate_quizzes.py
'''

📂 输出
生成文件：data/with_quizzes/slice_{0..3}_with_quizzes.jsonl
每个文件包含原始问题 + 生成的4个选项 + 正确答案
💡 提示：

如果使用本地模型，确保模型服务已启动
单次处理一个分块（脚本不会自动遍历4个切片，需要执行4次，为了控制文件大小）

### 🧠 步骤4：生成与评分推理轨迹
目标：用学生模型生成解题过程，并用评分模型评估质量

🛠️ 启动本地模型（根据老师模型情况吧）
# 赋予执行权限并运行
'''
chmod +x deploy_local_models.sh
./deploy_local_models.sh
'''
启动两个本地模型服务：
Student Model: Qwen 2.5 7B (http://localhost:8000)
Peer Model: Qwen 2.5 72B (http://localhost:8001)

🔑 配置评估脚本
编辑 generate_traces_and_grade.py：

确保地址和小模型准备好

### 🚀 执行命令
'''
python generate_traces_and_grade.py
'''
📂 输出
详细结果：results/details/slice_{0..3}_details.jsonl
包含字段：

### 📤 步骤5：合并与上传结果（可选）
目标：整合结果并上传至阿里云盘
