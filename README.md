# FBA 运价查询台

供应商 FBA 运价表拆解结果的查询页面（纯静态单文件）。

- **线上网址**：https://hijoelee.github.io/fba-rate-query/
- **项目说明、字段字典、更新流程**：见 [docs/README.md](docs/README.md)
- **决策记录、会话续接、待办**：见 [docs/DECISION_LOG.md](docs/DECISION_LOG.md)

---

## 本仓库主要内容

- `index.html`：查询页面（**唯一交付物**，同时是 GitHub Pages 根路径入口）
- `docs/`：项目文档（`README.md`、`DECISION_LOG.md`、`渲染基线.md`）
- `tools/`：**只读**辅助脚本（对话式查价 `chat_query.py`），见 [docs/README.md](docs/README.md) 的「tools/ 辅助脚本」

> 仓库不包含拆解框架、源表与内部数据，避免误外发。并入器与终检闸门在另一仓 `fba-rate-parser/tools/`。
