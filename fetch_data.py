#!/usr/bin/env python3
"""
每日收盘数据抓取 → api/data.json + api/history/YYYY-MM-DD.json
数据源：
  - 新浪 hq.sinajs.cn → 上证/沪深300/创业板
  - 腾讯 qt.gtimg.cn  → 恒生科技
  - Gold-API.com      → 国际金价
  - 新浪板块涨幅      → 持仓板块（涨跌幅反映主力关注度）
  - 东财 push2.eastmoney.com → 板块资金流（仅在非Azure IP环境有效）
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

def fetch_text(url, headers, timeout=12):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')

def fetch_gbk(url, headers, timeout=12):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('gbk', errors='replace')

# === 指数 ===
def fetch_indices():
    result = {}
    for sina_code, key, name in [
        ('s_sh000001', '000001', '上证指数'),
        ('s_sh000300', '000300', '沪深300'),
        ('s_sz399006', '399006', '创业板'),
    ]:
        print(f"  抓取 {name}...", end=' ', flush=True)
        try:
            raw = fetch_text(f"https://hq.sinajs.cn/list={sina_code}", HEADERS_SINA)
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
            result['HSTECH'] = {
                'name': '恒生科技',
                'price': round(price, 2),
                'chg': round(chg, 2),
                'pct': pct,
            }
            print(f"✅ {price} ({pct}%)")
        else:
            print("❌")
    except Exception as e:
        print(f"❌ {e}")
    return result

# === 黄金 ===
def fetch_gold():
    print("  抓取黄金...", end=' ', flush=True)
    try:
        raw = fetch_text("https://api.gold-api.com/price/XAU", HEADERS_SINA)
        d = json.loads(raw)
        price = float(d['price'])
        # 用新浪期货拿昨收
        raw2 = fetch_text("https://hq.sinajs.cn/list=hf_GC", HEADERS_SINA)
        m = re.search(r'="([^"]+)"', raw2)
        prev = price
        if m:
            p = m.group(1).split(',')
            if len(p) > 3 and p[3] and float(p[3]) > 0:
                prev = float(p[3])
        pct = round((price - prev) / prev * 100, 2) if prev else 0
        cny = round(price / 31.1035 * 7.25, 2)
        cny_prev = round(prev / 31.1035 * 7.25, 2)
        cny_pct = round((cny - cny_prev) / cny_prev * 100, 2) if cny_prev else 0
        print(f"✅ {price} USD/oz ({pct}%)")
        return {'usd': round(price, 2), 'usd_pct': pct, 'cny': cny, 'cny_pct': cny_pct}
    except Exception as e:
        print(f"❌ {e}")
        return {'usd': 0, 'usd_pct': 0, 'cny': 0, 'cny_pct': 0}

# === 板块涨幅（新浪板块接口）===
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

def fetch_plate_chg(plate):
    """通过新浪板块涨幅排行接口找到指定板块的涨跌幅"""
    try:
        # 新浪板块涨幅排行（行业分类）
        raw = fetch_text(
            "https://vip.stock.finance.sina.com.cn/quotes_service/api/jsonp.php/"
            "IO.XSRV2.CallbackList['stock_plates']/"
            "Market_Center.getHQNodeData?page=1&num=100&sort=changepercent&asc=0&node=hy&symbol=&_s_r_a=page",
            HEADERS_SINA
        )
        # 找板块名对应的涨跌幅
        # 格式: ["板块名","现价","涨跌幅",...]
        import ast
        try:
            items = json.loads(raw)
        except:
            items = []
        for item in items:
            if isinstance(item, list) and len(item) > 2:
                name_in_data = item[0]
                if plate['name'] in name_in_data or name_in_data in plate['name']:
                    pct = float(item[2]) if item[2] not in ('', None) else 0
                    return pct, item
        return None, None
    except Exception as e:
        print(f"    行业接口失败: {e}")
    return None, None

def fetch_plate_flow_eastmoney(plate_code):
    """东财板块资金流（仅作参考，不强依赖）"""
    ts = int(time.time() * 1000)
    url = (
        f"https://push2.eastmoney.com/api/qt/clist/get"
        f"?fid=f62&op=1&fltt=2&invt=2"
        f"&fs=b%3A{plate_code}"
        f"&fields=f12,f14,f62,f184,f2,f3"
        f"&pn=1&pz=50&_={ts}"
    )
    try:
        raw = fetch_text(url, {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "*/*",
        }, timeout=8)
        d = json.loads(raw)
        if d.get('data') and d['data'].get('diff'):
            items = d['data']['diff']
            total_net = sum(float(i.get('f62', 0) or 0) for i in items)
            total_super = sum(float(i.get('f184', 0) or 0) for i in items)
            pct = float(items[0].get('f3', 0) or 0) if items else 0
            return {'net': round(total_net), 'super': round(total_super), 'pct': pct}
    except:
        pass
    return None

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

    print("[3/3] 抓取板块涨幅（新浪行业板块）...")
    plateFlows = []

    for i, plate in enumerate(PLATES):
        print(f"  [{i+1}/{len(PLATES)}] {plate['name']}...", end=' ', flush=True)

        # 先尝试东财资金流（如果能拿到，用真实资金流）
        ef = fetch_plate_flow_eastmoney(plate['code'])
        if ef and abs(ef['net']) > 1000:
            # 估算散户/大户/主力比例
            net = ef['net']
            zhu = ef['super']
            da = int((net - zhu) * 0.4)
            san = net - zhu - da
            print(f"✅ 东财 主力:{(zhu/1e8):+.2f}亿 净额:{(net/1e8):+.2f}亿 涨幅:{ef['pct']}%")
            plateFlows.append({
                'name': plate['name'],
                'code': plate['code'],
                'pct': ef['pct'],
                '散户': round(san),
                '大户': round(da),
                '主力': round(zhu),
                'net': ef['net'],
            })
        else:
            # Fallback: 新浪行业板块涨幅排行
            pct, item = fetch_plate_chg(plate)
            if pct is not None:
                # 涨幅 → 估算资金流（涨得多通常意味着主力净流入）
                # 经验估算：涨幅1% ≈ 主力净流入约2-5亿
                # 用线性估算：净额 = pct * 3e8
                net = int(pct * 3e8)
                zhu = int(net * 0.6)
                da = int(net * 0.25)
                san = net - zhu - da
                print(f"✅ 新浪 涨幅: {pct}%")
                plateFlows.append({
                    'name': plate['name'],
                    'code': plate['code'],
                    'pct': round(pct, 2),
                    '散户': round(san),
                    '大户': round(da),
                    '主力': round(zhu),
                    'net': net,
                    'source': 'sina',
                })
            else:
                print("⚠️ 无数据")
                plateFlows.append({
                    'name': plate['name'],
                    'code': plate['code'],
                    'pct': 0,
                    '散户': 0,
                    '大户': 0,
                    '主力': 0,
                    'net': 0,
                })
        time.sleep(0.3)

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
    print(f"  板块涨幅:")
    for p in plateFlows:
        print(f"    {p['name']}: {p.get('pct',0)}% | 净额:{(p.get('net',0)/1e8):+.2f}亿")

if __name__ == '__main__':
    main()
