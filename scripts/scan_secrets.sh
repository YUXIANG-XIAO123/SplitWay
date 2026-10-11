#!/usr/bin/env sh
# A2：凭据扫描。在仓库源码（.py / .yml / .yaml / Dockerfile）中查找疑似明文凭据。
# 退出码 0 表示未发现硬编码凭据；发现命中则退出码非 0。
#
# 用法：sh scripts/scan_secrets.sh
#
# 说明：正则刻意避开占位符（change_me / example / ${VAR} 等），只报告疑似真实凭据。

set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[scan] 扫描目录: $ROOT_DIR"

# 嫌疑模式：password/secret/token 后紧跟 = 或 : ，且等号右侧不是占位符或环境变量引用。
PATTERN='(password|passwd|secret|token)[[:space:]]*[:=][[:space:]]*[^$[:space:]]'

MATCHES="$(grep -rnE "$PATTERN" \
  --include='*.py' --include='*.yml' --include='*.yaml' \
  --include='Dockerfile' \
  --exclude-dir='node_modules' --exclude-dir='.git' --exclude-dir='.venv' \
  . || true)"

# 过滤掉占位符与变量引用。
MATCHES="$(printf '%s\n' "$MATCHES" | grep -vE 'change_me|example|CHANGE_ME|placeholder|your_|\$\{' || true)"

if [ -n "$MATCHES" ]; then
  echo "[scan] 发现疑似硬编码凭据："
  printf '%s\n' "$MATCHES"
  exit 1
fi

echo "[scan] 未发现硬编码凭据，通过。"
exit 0
