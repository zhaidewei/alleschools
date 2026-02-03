#!/usr/bin/env bash
# pre-commit 用：跑 Python 单元测试 + 前端逻辑 (Node) 单元测试
set -e
cd "$(dirname "$0")"

# Python（只收集 .py）
if [ -f .venv/bin/pytest ]; then
  .venv/bin/pytest tests/ -v
else
  pytest tests/ -v
fi

# 前端纯逻辑 (Node 内置 test runner)
node --test tests/view_xy_logic.test.js
