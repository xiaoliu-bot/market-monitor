# backup/ — 原 Market Monitor 看板归档

> 归档日期：2026-07-31
> 本目录是原「Market Monitor 市场监控面板」的完整备份，**已停止运行**，仅作存档。

本仓库已改造为「看板聚合站」（根目录 `index.html`），原看板不再上线。原看板的全部代码、数据脚本、GitHub Actions 均归档于此。

## 归档文件清单

| 文件 / 目录 | 说明 |
|---|---|
| `market-monitor.html` | 原看板页面（HTML+CSS+JS 单文件，约 950 行） |
| `fetch_data.py` | 数据抓取脚本（AKShare 全数据源） |
| `api/data.json` | 节假日 / 收盘后兜底数据 |
| `api/history/` | 历史数据快照 |
| `scripts/fetch_data.py` | 抓取脚本副本 |
| `scripts/github_push.py` | GitHub 推送辅助脚本 |
| `design/` | 设计稿（Ardot 导出 PDF + 气泡图原型） |
| `workflows/daily-fetch.yml` | GitHub Actions：每日自动抓取（归档后已停止） |
| `workflows/update-market.yml` | GitHub Actions：市场数据更新（归档后已停止） |
| `README.md` | 原技术文档 |

## 如何恢复运行

如需重新上线原看板：

1. 将 `market-monitor.html` 移回根目录并改名为 `index.html`（注意会让聚合站失效，请先备份当前聚合站 `index.html`）
2. 将 `workflows/*.yml` 移回 `.github/workflows/`（需先创建 `.github/workflows/` 目录）
3. 将 `fetch_data.py`、`api/`、`scripts/` 移回根目录
4. 推送后 GitHub Actions 会恢复自动抓取

> 注意：归档后 `workflows/` 不在 `.github/workflows/` 路径下，GitHub Actions **不会触发**，即数据抓取已停止。
