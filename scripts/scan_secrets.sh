#!/usr/bin/env sh
# A2 / C3：凭据扫描。
#
# 设计说明（为什么不是"全仓关键词搜索"）：
#   本项目里 password / token 是**正常的领域词**（登录、鉴权），全仓扫会产生大量误报 ——
#   例如 `password: str` 这类类型注解、`password = "pass1234"` 这类测试夹具。
#   误报的代价比漏报更高：一个常红的闸门会训练人忽略它。
#
# 因此收窄为两条：
#   ① 只扫**凭据真正会出现的地方**（编排 / 镜像 / 工作流 / 环境变量样例 / 后端配置）；
#   ② 只匹配**大写凭据键 + 字面量值**（环境变量风格），并要求值不是 ${VAR} 引用或占位符。
#
# 用法：sh scripts/scan_secrets.sh
# 退出码 0 = 未发现；1 = 发现疑似真实凭据。

set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

TARGETS=""
for f in docker-compose.yml .env.example backend/app/config.py Dockerfile \
         backend/Dockerfile frontend/Dockerfile; do
  [ -f "$f" ] && TARGETS="$TARGETS $f"
done
for f in .github/workflows/*.yml .github/workflows/*.yaml; do
  [ -f "$f" ] && TARGETS="$TARGETS $f"
done

echo "[scan] 目标文件："
for t in $TARGETS; do echo "       $t"; done

# 大写凭据键（环境变量风格）后跟 : 或 =，右侧为非空白且非 $ 开头的字面量。
PATTERN='(PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|APIKEY|ACCESS_KEY)[^A-Za-z]*[:=][[:space:]]*[^$[:space:]]+'

FOUND=""
for t in $TARGETS; do
  hit="$(grep -nE "$PATTERN" "$t" 2>/dev/null | grep -viE 'change_me|example|placeholder|your_|\$\{' || true)"
  if [ -n "$hit" ]; then
    FOUND="$FOUND
--- $t
$hit"
  fi
done

if [ -n "$FOUND" ]; then
  echo "[scan] 发现疑似硬编码凭据：$FOUND"
  exit 1
fi

echo "[scan] 未发现硬编码凭据，通过。"
exit 0
