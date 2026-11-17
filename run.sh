#!/bin/bash
# StudyHack 平台启动脚本（部署沙箱用）
# 监听 $PORT 环境变量，绑定 0.0.0.0，满足单端口 HTTP 服务部署要求
set -e
exec streamlit run app.py \
  --server.port="${PORT:-8501}" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
