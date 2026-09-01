# FBA 运价查询台

供应商 FBA 运价表拆解结果的查询页面（纯静态单文件）。

- **线上网址**：https://hijoelee.github.io/fba-rate-query/
- 数据源：fba_rate_parser 框架拆解输出（皓鹏国际同行vip8月31日，4 个来源表，447 条记录）
- 技术：单文件 HTML + 内嵌 JSON，零依赖、免后端、免登录、手机自适应
- 部署：GitHub Pages（推送 `main` 分支自动部署，免费无次数限制）

## 更新流程

1. 用 fba_rate_parser 拆解新表 → 确认 → 导出页面数据
2. 重新生成 `fba-rate-query.html`，并复制为 `index.html`（GitHub Pages 根路径入口）
3. `git add . && git commit -m "update: <说明>" && git push origin main`
4. GitHub Actions 自动部署，约 1-2 分钟生效

## 本仓库内容

- `fba-rate-query.html`：查询页面（主交付物）
- `index.html`：根路径入口（与主文件内容一致）
- 拆解框架/源表/内部数据**不入本仓库**（保持干净，便于外发）
