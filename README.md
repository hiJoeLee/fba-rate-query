# FBA 运价查询台

供应商 FBA 运价表拆解结果的查询页面（纯静态单文件）。

- **线上网址**：https://fba-rate-query.netlify.app
- 数据源：fba_rate_parser 框架拆解输出（皓鹏国际同行vip8月31日，4 个来源表，447 条记录）
- 技术：单文件 HTML + 内嵌 JSON，零依赖、免后端、免登录、手机自适应
- 部署：Netlify 站点 `fba-rate-query`（site id `bccf5710-d9ee-4cfc-bfdc-931878abd0a6`）

## 更新流程（手动部署，当前生效）

1. 用 fba_rate_parser 拆解新表 → 确认 → 导出页面数据
2. 重新生成 `fba-rate-query.html`，并复制为 `index.html`（Netlify 根路径入口）
3. `git add . && git commit -m "update: <说明>" && git push origin main`
4. 部署：`netlify deploy --dir . --prod --site bccf5710-d9ee-4cfc-bfdc-931878abd0a6`（需 `NETLIFY_AUTH_TOKEN` 环境变量）

> 注：Netlify 生产 URL 公开可访问（SSO 仅保护预览部署）。

## 本仓库内容

- `fba-rate-query.html`：查询页面（主交付物）
- `index.html`：根路径入口（与主文件内容一致）
- 拆解框架/源表/内部数据**不入本仓库**（保持干净，便于外发）
