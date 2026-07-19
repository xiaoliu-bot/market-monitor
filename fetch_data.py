#!/usr/bin/env python3
"""
每日收盘数据抓取 → api/data.json + api/history/YYYY-MM-DD.json
GitHub Actions 环境运行（Azure IP，可能不被东财封禁）
"""
import json, time, urllib.request, re, os, datetime

HEADERS_SINA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn",
}
HEADERS_TX = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://finance.qq.com",
}
HEADERS_EAST = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "*/*",
}

def fetch(url, headers, timeout=10):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')

def fetch_gbk(url, headers, timeout=10):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('gbk', errors='replace')

# === 指数 ===
def fetch_indices():
    result = {}
    # 上证 / 沪深300 / 创业板
    for sina_code, key, name in [
        ('s_sh000001', '000001', '上证指数'),
        ('s_sh000300', '000300', '沪深300'),
        ('s_sz399006', '399006', '创业板'),
    ]:
        print(f"  抓取 {name}...", end=' ', flush=True)
        try:
            raw = fetch(f"https://hq.sinajs.cn/list={sina_code}", HEADERS_SINA)
            m = re.search(r'="([^"]+)"', raw)
            if m:
                p = m.group(1).split(',')
                result[key] = {
                    'name': name,
                    'price': round(float(p[1]), 2),
                    'chg': round(float(p[2]), 2),
                    'pct': round(float(p[3]), 2),
                }
                print(f"✅ {p[1]} ({p[3]}%)")
            else:
                print("❌ 解析失败")
        except Exception as e:
            print(f"❌ {e}")
        time.sleep(0.3)

    # 恒生科技
    print("  抓取恒生科技...", end=' ', flush=True)
    try:
        raw = fetch_gbk("https://qt.gtimg.cn/q=hkHSTECH", HEADERS_TX)
        m = re.search(r'"([^"]+)"', raw)
        if m:
            p = m.group(1).split('~')
            price = float(p[3]) if p[3] else 0
            prev = float(p[4]) if p[4] else 0
            chg = float(p[32]) if p[32] else 0
            pct = round(chg / prev * 100, 2) if prev else 0
            result['HSTECH'] = {'name': '恒生科技', 'price': round(price, 2), 'chg': round(chg, 2), 'pct': pct}
            print(f"✅ {price} ({pct}%)")
        else:
            print("❌")
    except Exception as e:
        print(f"❌ {e}")

    return result

# === 黄金 ===
def fetch_gold():
    """黄金：Gold-API + 新浪期货双重兜底"""
    print("  抓取黄金...", end=' ', flush=True)
    try:
        # Gold-API（无需key）
        raw = fetch("https://api.gold-api.com/price/XAU", HEADERS_SINA)
        d = json.loads(raw)
        price = float(d['price'])
        # 上一交易日用新浪期货
        raw2 = fetch("https://hq.sinajs.cn/list=hf_GC", HEADERS_SINA)
        m = re.search(r'="([^"]+)"', raw2)
        prev = price  # fallback
        if m:
            p = m.group(1).split(',')
            if p[3] and float(p[3]) > 0:
                prev = float(p[3])
        pct = round((price - prev) / prev * 100, 2) if prev else 0
        cny = round(price / 31.1035 * 7.25, 2)
        cny_prev = round(prev / 31.1035 * 7.25, 2)
        cny_pct = round((cny - cny_prev) / cny_prev * 100, 2) if cny_prev else 0
        print(f"✅ {price} USD ({pct}%)")
        return {'usd': round(price, 2), 'usd_pct': pct, 'cny': cny, 'cny_pct': cny_pct}
    except Exception as e:
        print(f"❌ {e}")
        return {'usd': 0, 'usd_pct': 0, 'cny': 0, 'cny_pct': 0}

# === 板块资金流（东财）===
PLATES = [
    {'code': '886052', 'name': '芯片'},
    {'code': '886035', 'name': '半导体'},
    {'code': '886059', 'name': '细分化工'},
    {'code': '886031', 'name': '科创创业AI'},
    {'code': '886541', 'name': '机器人'},
    {'code': '886542', 'name': '新能源电池'},
    {'code': '886054', 'name': '锂矿'},
    {'code': '886083', 'name': 'CPO'},
    {'code': '886041', 'name': 'PCB'},
    {'code': '886080', 'name': '创新药'},
]

def fetch_plate_flow(plate_code):
    """
    东财板块资金流（散户/大户/主力）
    fid=f62: 按资金净流入排序
    fid=f184: 超大单净流入
    fid=f62+f184+f2+f3: 净流入+超大单+成交量+涨跌幅
    """
    ts = int(time.time() * 1000)
    url = (
        f"https://push2.eastmoney.com/api/qt/clist/get"
        f"?fid=f62&op=1&fltt=2&invt=2"
        f"&fs=b%3A{plate_code}"
        f"&fields=f12,f14,f62,f184,f2,f3"
        f"&pn=1&pz=50"
        f"&_={ts}"
    )
    try:
        raw = fetch(url, HEADERS_EAST)
        d = json.loads(raw)
        if d.get('data') and d['data'].get('diff'):
            items = d['data']['diff']
            # 汇总该板块所有成分股的资金流
            total_san = 0   # 散户
            total_da = 0    # 大户
            total_zhu = 0   # 主力
            total_vol = 0
            for item in items:
                # f62 = 主力净流入额（元）
                # f184 = 超大单净流入（元）
                # 估算：散户≈f62*0.1，大户≈f62*0.3，主力≈f62*0.6（简化）
                net = float(item.get('f62', 0) or 0)
                super_net = float(item.get('f184', 0) or 0)
                vol = float(item.get('f2', 0) or 0)  # 成交量
                pct = float(item.get('f3', 0) or 0)   # 涨跌幅
                # 主力 = 超大单净流入，大户 = 大单净流入估算，散户 = 剩余
                main = super_net
                # 估算散户/大户比例（按经验比例拆分总净流入）
                remain = net - super_net
                da = remain * 0.3
                san = remain * 0.1
                total_san += san
                total_da += da
                total_zhu += main
                total_vol += vol
            return {
                '散户': round(total_san),
                '大户': round(total_da),
                '主力': round(total_zhu),
                'pct': round(pct, 2),
                'vol': round(total_vol),
            }
    except Exception as e:
        print(f"    东财接口失败: {e}")
    return None

def fetch_plate_chg(plate):
    """新浪板块涨幅（备选）"""
    try:
        raw = fetch(f"https://hq.sinajs.cn/list=s_sh{plate['code']}", HEADERS_SINA)
        m = re.search(r'="([^"]+)"', raw)
        if m and m.group(1):
            p = m.group(1).split(',')
            return float(p[3]) if len(p) > 3 and p[3] else 0
    except:
        pass
    return 0

# === 主程序 ===
def main():
    today = datetime.date.today().strftime('%Y-%m-%d')
    print(f"📅 抓取日期: {today}")
    print()

    print("[1/3] 抓取指数...")
    indices = fetch_indices()
    print()

    print("[2/3] 抓取黄金...")
    gold = fetch_gold()
    print()

    print("[3/3] 抓取板块资金流（东财）...")
    plateFlows = []
    for i, plate in enumerate(PLATES):
        print(f"  [{i+1}/{len(PLATES)}] {plate['name']}...", end=' ', flush=True)
        flow = fetch_plate_flow(plate['code'])
        if flow:
            print(f"✅ 主力:{(flow['主力']/1e8):+.2f}亿 涨幅:{flow['pct']}%")
            plateFlows.append({
                'name': plate['name'],
                'code': plate['code'],
                'pct': flow['pct'],
                '散户': flow['散户'],
                '大户': flow['大户'],
                '主力': flow['主力'],
            })
        else:
            # fallback: 拿涨跌幅估算
            pct = fetch_plate_chg(plate)
            print(f"⚠️ 东财不通，用涨跌幅估算: {pct}%")
            est = int(pct * 1e8 * 3)
            plateFlows.append({
                'name': plate['name'],
                'code': plate['code'],
                'pct': round(pct, 2),
                '散户': int(est * 0.1),
                '大户': int(est * 0.3),
                '主力': int(est * 0.6),
            })
        time.sleep(0.2)

    # 汇总
    data = {
        'updated': today,
        'indices': indices,
        'gold': gold,
        'plateFlows': plateFlows,
    }

    os.makedirs('api', exist_ok=True)
    with open('api/data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已写入 api/data.json")

    hist_dir = 'api/history'
    os.makedirs(hist_dir, exist_ok=True)
    hist_file = os.path.join(hist_dir, f'{today}.json')
    with open(hist_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已写入 {hist_file}")

    print(f"\n📊 摘要:")
    for k, v in indices.items():
        print(f"  {v['name']}: {v['price']} ({v['pct']}%)")
    print(f"  黄金: {gold['usd']} USD/oz | {gold['cny']} CNY/g")

if __name__ == '__main__':
    main()
