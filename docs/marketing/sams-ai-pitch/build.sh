#!/usr/bin/env bash
# 构建坤爵客户推介 PDF
# 用法: ./build.sh
# 需要: Node.js + Google Chrome
# 首次运行:cd 到本目录并 npm install
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [[ ! -d node_modules ]]; then
  echo "[setup] 安装依赖..."
  npm install --no-audit --no-fund
fi

node render.js
