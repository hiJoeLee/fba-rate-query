#!/usr/bin/env bash
# 一键发布：feat/计费 → main → GitHub Pages 自动更新
# 用法：bash query/tools/deploy.sh （在 query 仓库任意目录下执行）
set -e

cd "$(dirname "$0")/.."

echo "== 1/5 检查工作区 =="
if [ -n "$(git status --porcelain)" ]; then
  echo "工作区有未提交改动，请先提交或 stash，再重新执行："
  git status --porcelain
  exit 1
fi

echo "== 2/5 推送 feat/计费 =="
git push origin feat/计费

echo "== 3/5 合并到 main =="
git checkout main
git merge --ff-only feat/计费
git push origin main

echo "== 4/5 切回开发分支 =="
git checkout feat/计费

echo "== 5/5 完成 =="
echo "GitHub Pages 约 1-3 分钟自动更新："
echo "  https://hijoelee.github.io/fba-rate-query/"
