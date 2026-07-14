#!/bin/bash
# CPU only モードのサンプル。
# cp configs/cpu_only.sample.sh configs/cpu_only.sh してからローカル設定を編集する。

MODEL_PATH="models/your-model/model.gguf"
# MMPROJ_PATH="models/your-model/mmproj.gguf"
# ALIAS="your-model"

# MTP は CPU only でも使用可能。主モデルに対応する GGUF を指定する。
# SPEC_DRAFT_MODEL_PATH="models/your-model/mtp-model.gguf"
# SPEC_TYPE="draft-mtp"
# SPEC_DRAFT_N_MAX=3
# SPEC_DRAFT_N_MIN=0
# SPEC_DRAFT_N_GPU_LAYERS=0

N_GPU_LAYERS=0
# THREADS=-1
# THREADS_BATCH=-1
# CPU_MASK=""
# NUMA=""

# CPU only ではメモリ消費を抑えるため明示指定を推奨
CTX_SIZE=8192
# BATCH_SIZE=2048
# UBATCH_SIZE=512
# CACHE_TYPE_K="f16"
# CACHE_TYPE_V="f16"
# MLOCK=false

PARALLEL=1
# CONT_BATCHING=true
# KV_UNIFIED=true

HOST="0.0.0.0"
PORT=8080
# API_KEY=""
# TIMEOUT=600
# THREADS_HTTP=-1

# JINJA=true
# REASONING_FORMAT=""
# REASONING_BUDGET=0
# CHAT_TEMPLATE_KWARGS='{"enable_thinking": true}'

# PRIO=0
# LOG_VERBOSITY=3
