# FBA 运价查询台

供应商 FBA 运价表拆解结果的查询页面（纯静态单文件）。

- 数据源：fba_rate_parser 框架拆解输出（皓鹏国际同行vip8月31日，4 个来源表，447 条记录）
- 技术：单文件 HTML + 内嵌 JSON，零依赖、免后端、免登录
- 部署：Netlify 连接本仓库，build 命令留空，publish 目录填 `.`，push 即自动部署

## 更新流程

1. 用 fba_rate_parser 拆解新表 → 确认 → 导出页面数据
2. 重新生成 `fba-rate-query.html`
3. `git add fba-rate-query.html && git commit -m "update: <说明>" && git push`
4. Netlify 自动部署，链接不变

## 本仓库内容

- `fba-rate-query.html`：查询页面（唯一交付物，git 追踪）
- 拆解框架/源表/内部数据**不入本仓库**（保持干净，便于外发）
