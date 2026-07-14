#!/bin/bash
# CPU + GPU 混合モードのサンプル。
# cp configs/cpu_gpu.sample.sh configs/cpu_gpu.sh してからローカル設定を編集する。

# 必須: プロジェクトルートからの相対パス、または絶対パス
MODEL_PATH="models/your-model/model.gguf"

# Vision モデルの場合だけ指定
# MMPROJ_PATH="models/your-model/mmproj.gguf"
# ALIAS="your-model"

# MTP を使う場合だけ、主モデルに対応する assistant/MTP GGUF を指定
# 例（Gemma 4 12B QAT）:
# SPEC_DRAFT_MODEL_PATH="models/gemma4/mtp-gemma-4-12B-it.gguf"
# SPEC_TYPE="draft-mtp"
# SPEC_DRAFT_N_MAX=3
# SPEC_DRAFT_N_MIN=0
# SPEC_DRAFT_N_GPU_LAYERS=auto
# SPEC_DRAFT_DEVICE="CUDA0"

# GPU / CPU バランス。auto は利用可能な VRAM に応じて自動調整する。
N_GPU_LAYERS=auto
# FLASH_ATTN="auto"

# CPU
# THREADS=auto
# THREADS_BATCH=-1
# NUMA=""

# メモリ
CTX_SIZE=8192
# BATCH_SIZE=2048
# UBATCH_SIZE=512
# CACHE_TYPE_K="f16"
# CACHE_TYPE_V="f16"
# MLOCK=false

# 並列・スループット
PARALLEL=1
# CONT_BATCHING=true
# KV_UNIFIED=true

# サーバー
HOST="0.0.0.0"
PORT=8080
# API_KEY=""
# TIMEOUT=600
# THREADS_HTTP=-1

# モデル固有オプション
# JINJA=true
# REASONING_FORMAT=""
# REASONING_BUDGET=0
# CHAT_TEMPLATE_KWARGS='{"enable_thinking": true}'

# PRIO=0
# LOG_VERBOSITY=3
