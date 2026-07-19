#!/usr/bin/env python3
"""
抓取市场数据写入 api/data.json
用于节假日/收盘后兜底
数据源：新浪财经 + 腾讯证券 + Yahoo Finance
"""
import json, time, urllib.request, re

HEADERS_SINA = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://finance.sina.com.cn",
}
HEADERS_TX = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://finance.qq.com",
}

def fetch(url, headers, timeout=10):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("gbk", errors="replace")

def fetch_yahoo(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def parse_sina(raw, field_idx):
    """从新浪格式解析字段，如 raw='sh000001=..." """
    m = re.search(r'="([^"]+)"', raw)
    if not m: return None
    parts = m.group(1).split(",")
    try: return float(parts[field_idx])
    except: return None

def fetch_indices():
    result = {}
    # 上证指数
    raw = fetch("https://hq.sinajs.cn/list=s_sh000001", HEADERS_SINA)
    parts = re.search(r'="([^"]+)"', raw)
    if parts:
        p = parts.group(1).split(",")
        result["000001"] = {
            "price": round(float(p[3]), 2),
            "pct": round(float(p[3]) - float(p[2]), 2),
            "name": "上证指数",
            "raw_str": parts.group(1)
        }
    time.sleep(0.3)
    # 恒生科技 - 腾讯
    raw = fetch("https://qt.gtimg.cn/q=rt_HSTECH", HEADERS_TX)
    # 格式: v_rt_HSTECH="1~恒生科技~HSTECH~..."
    m = re.search(r'"([^"]+)"', raw)
    if m:
        p = m.group(1).split("~")
        # p[3]=当前价, p[4]=昨收, p[32]=涨跌额, p[33]=涨跌幅
        price = float(p[3]) if p[3] else 0
        pct = float(p[33]) if p[33] else 0
        result["HSTECH"] = {
            "price": round(price, 2),
            "pct": round(pct, 2),
            "name": "恒生科技"
        }
    return result

def fetch_gold():
    """黄金：Yahoo Finance GC=F（纽约金）"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=1d&range=5d"
    d = fetch_yahoo(url)
    meta = (d.get("chart") or {}).get("result", [{}])[0].get("meta", {})
    price = meta.get("regularMarketPrice", 0) or 0
    prev = meta.get("previousClose", price) or price
    pct = round((price - prev) / prev * 100, 2) if prev else 0
    # USD/oz → CNY/g，汇率用固定7.25
    cny = round(price / 31.1035 * 7.25, 2)
    cny_prev = round(prev / 31.1035 * 7.25, 2)
    cny_pct = round((cny - cny_prev) / cny_prev * 100, 2) if cny_prev else 0
    return {
        "usd": round(price, 2),
        "usd_pct": pct,
        "cny": cny,
        "cny_pct": cny_pct,
    }

def fetch_plate_flow(plate):
    """板块资金流 - 腾讯证券板块接口"""
    # 腾讯板块涨幅接口
    url = f"https://qt.gtimg.cn/q=s_{plate['code']}"
    raw = fetch(url, HEADERS_TX)
    # 格式: v_s_886052="..."~现价~涨跌幅~... 或 未知格式
    # 改用新浪板块列表
    url2 = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/jsonp.php/IO.XSRV2.CallbackList['stock_plates']/Market_Center.getHQNodeData?page=1&num=20&sort=changepercent&asc=0&node={plate['code']}&symbol=&_s_r_a=page"
    try:
        raw2 = fetch(url2, HEADERS_SINA)
    except Exception as e:
        print(f"    [{plate['name']}] 新浪失败: {e}")
        return None
    # 返回原始字符串供调试
    return {"raw": raw2[:100]}

def main():
    plates = [
        {"code": "886052", "name": "芯片"},
        {"code": "886035", "name": "半导体"},
        {"code": "886059", "name": "细分化工"},
        {"code": "886031", "name": "科创创业AI"},
        {"code": "886541", "name": "机器人"},
        {"code": "886542", "name": "新能源电池"},
        {"code": "886054", "name": "锂矿"},
        {"code": "886083", "name": "CPO"},
        {"code": "886041", "name": "PCB"},
        {"code": "886080", "name": "创新药"},
    ]

    data = {
        "updated": "2026-07-17 15:00",
        "indices": fetch_indices(),
        "gold": fetch_gold(),
        "plateFlows": []
    }
    print("指数:", data["indices"])
    print("黄金:", data["gold"])

    for i, plate in enumerate(plates):
        print(f"[{i+1}/{len(plates)}] 抓取 {plate['name']}...")
        flow = fetch_plate_flow(plate)
        data["plateFlows"].append({"name": plate["name"], "code": plate["code"], "flow": flow})
        time.sleep(0.3)

    with open("api/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已写入 api/data.json")
    print(json.dumps(data, ensure_ascii=False, indent=2)[:800])

if __name__ == "__main__":
    main()
