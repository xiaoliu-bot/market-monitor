# 看板总览 · 数据中枢

> Dashboard Hub · A股 / ETF / 指数 实时监控聚合入口
> 线上地址：https://xiaoliu-bot.github.io/market-monitor/

本仓库仅作为**看板聚合站**，汇总小刘的三个金融数据看板入口。原「Market Monitor」看板已归档至 [`backup/`](./backup/) 目录，不再运行。

## 聚合看板

| 看板 | 地址 | 说明 |
|---|---|---|
| 📈 ETF 技术分析看板 | https://xiaoliu-bot.github.io/ETF-recommend/ | 16 只板块 ETF 技术评分与操作信号，K 线指标 + 政策新闻 |
| 🔥 小白指数看板 | https://xiaoliu-bot.github.io/babymom-dashboard/ | 大盘指数监控，板块热力图与估值百分位对比 |
| 🌐 智瞰 · 实时财经看板 | https://xiaoliu-bot.github.io/white-dashbord/ | 大盘指数 + 中信期指多空 + 板块异动 + 资金流气泡图 |

## 文件结构

```
market-monitor/
├── index.html        # 聚合站首页（黑底金融风格，3 卡片网格）
├── README.md         # 本文件
└── backup/           # 原 Market Monitor 看板归档（已停止运行）
    ├── ARCHIVE.md        # 归档说明与恢复方法
    ├── market-monitor.html
    ├── fetch_data.py
    ├── api/  scripts/  design/  workflows/  README.md
```

## 配色规范

红涨绿跌，遵循 A 股惯例：
- 涨 / 流入 / 吸筹 → 红色 `#ff4444`
- 跌 / 流出 → 绿色 `#44ff88`
- 背景 → 黑色 `#000`，卡片 `#0a0a0a` / `#111`

> 数据来源：东方财富 · Yahoo Finance · Gold-API
> 仅作个人监控参考，不构成投资建议。
