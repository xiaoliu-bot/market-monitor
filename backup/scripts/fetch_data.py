#!/usr/bin/env python3
"""
更新 api/data.json - 使用 Tushare + 东方财富
"""
import json
import urllib.request
import urllib.error
import time
from datetime import datetime

# ========== Tushare ==========
try:
    import tushare as ts
    TUSHARE_TOKEN = '0cdd5c099fd79ce5b598c77d97dd1ad1ec86aedeb22c77756222c4d2'
    ts.set_token(TUSHARE_TOKEN)
    PRO = ts.pro_api()
    TUSHARE_OK = True
    print("✅ Tushare 已连接")
except Exception as e:
    PRO = None
    TUSHARE_OK = False
    print(f"⚠️ Tushare 初始化失败: {e}")

def tushare_get(func, **kwargs):
    """Tushare 接口封装（带重试）"""
    if not TUSHARE_OK:
        return None
    for attempt in range(2):
        try:
            return func(**kwargs)
        except Exception as e:
            if 'frequency' in str(e) or 'limit' in str(e):
                print(f"  ⚠️ Tushare 频率限制，{attempt+1}秒后重试...")
                time.sleep(3)
            else:
                print(f"  ⚠️ Tushare 错误: {e}")
                return None
    return None

def fetch_json(url, headers=None):
    """通用 HTTP GET"""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.eastmoney.com',
        **(headers or {})
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠️ HTTP 请求失败: {e}")
        return None

def load_existing():
    """读取现有 data.json"""
    try:
        with open('api/data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    """保存 data.json"""
    with open('api/data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("  ✅ 已保存 api/data.json")

# ========== 大盘指数 ==========
def load_indices():
    """加载大盘指数（优先 Tushare，降级东方财富）"""
    indices = {}
    today = datetime.now().strftime('%Y%m%d')
    
    # 获取最新交易日
    if TUSHARE_OK:
        cal = tushare_get(PRO.trade_cal, exchange='SSE', end_date=today, is_open='1')
        if cal is not None and len(cal) > 0:
            trade_date = cal.iloc[-1]['cal_date']
        else:
            trade_date = today
    else:
        trade_date = today
    
    # 1. 上证指数
    if TUSHARE_OK:
        df = tushare_get(PRO.index_daily, ts_code='000001.SH', limit=1)
        if df is not None and len(df) > 0:
            row = df.iloc[0]
            indices['sh'] = {
                'name': '上证指数',
                'price': round(float(row['close']), 2),
                'pct': round(float(row['pct_chg']), 2),
                'time': str(row['trade_date'])
            }
            print(f"  📈 上证(Tushare): {row['close']:.2f} ({row['pct_chg']:+.2f}%)")
    
    if 'sh' not in indices:
        # 降级东方财富
        url = "https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f43,f57,f58,f169,f170,f47,f48"
        d = fetch_json(url)
        if d and d.get('data'):
            data = d['data']
            price = data.get('f43', 0) / 100
            pct = data.get('f170', 0) / 100
            indices['sh'] = {
                'name': '上证指数',
                'price': round(price, 2),
                'pct': round(pct, 2),
                'time': data.get('f58', '')
            }
            print(f"  📈 上证(东财): {price:.2f} ({pct:+.2f}%)")
    
    time.sleep(1)
    
    # 2. 沪深300
    if TUSHARE_OK:
        df = tushare_get(PRO.index_daily, ts_code='000300.SH', limit=1)
        if df is not None and len(df) > 0:
            row = df.iloc[0]
            indices['hs300'] = {
                'name': '沪深300',
                'price': round(float(row['close']), 2),
                'pct': round(float(row['pct_chg']), 2),
            }
            print(f"  📈 沪深300(Tushare): {row['close']:.2f} ({row['pct_chg']:+.2f}%)")
    
    time.sleep(1)
    
    # 3. 纳斯达克（Yahoo）
    url = "https://query1.finance.yahoo.com/v8/finance/chart/IXIC?interval=1d&range=2d"
    d = fetch_json(url, headers={'User-Agent': 'Mozilla/5.0'})
    if d and d.get('chart', {}).get('result'):
        result = d['chart']['result'][0]
        meta = result['meta']
        price = meta.get('regularMarketPrice', 0)
        prev = meta.get('previousClose', price)
        pct = (price - prev) / prev * 100 if prev else 0
        indices['nasdaq'] = {
            'name': '纳斯达克',
            'price': round(price, 2),
            'pct': round(pct, 2),
            'prevClose': round(prev, 2)
        }
        print(f"  📈 纳指(Yahoo): {price:.2f} ({pct:+.2f}%)")
    
    time.sleep(0.5)
    
    # 4. 恒生科技
    url = "https://push2.eastmoney.com/api/qt/stock/get?secid=116.HSTECH&fields=f43,f57,f58,f169,f170,f47,f48"
    d = fetch_json(url)
    if d and d.get('data'):
        data = d['data']
        price = data.get('f43', 0) / 100
        pct = data.get('f170', 0) / 100
        indices['hstech'] = {
            'name': '恒生科技',
            'price': round(price, 2),
            'pct': round(pct, 2),
            'time': data.get('f58', '')
        }
        print(f"  📈 恒科(东财): {price:.2f} ({pct:+.2f}%)")
    
    return indices

# ========== 黄金 ==========
def load_gold():
    """加载黄金数据"""
    gold = {}
    
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=1d&range=5d"
    d = fetch_json(url, headers={'User-Agent': 'Mozilla/5.0'})
    if d and d.get('chart', {}).get('result'):
        result = d['chart']['result'][0]
        closes = result['indicators']['quote'][0]['close']
        last = closes[-1]
        prev = closes[-2] if len(closes) > 1 else last
        pct = (last - prev) / prev * 100 if prev else 0
        
        gold['usd'] = round(last, 2)
        gold['usd_pct'] = round(pct, 2)
        
        usd_cny = 7.25
        cny_gold = last * usd_cny / 31.1035
        cny_prev = prev * usd_cny / 31.1035
        cny_pct = (cny_gold - cny_prev) / cny_prev * 100 if cny_prev else 0
        
        gold['cny'] = round(cny_gold, 2)
        gold['cny_pct'] = round(cny_pct, 2)
        
        recent = closes[-5:]
        trend = recent[-1] - recent[0]
        if trend > 10:
            prediction = "近期强势上涨，注意获利了结压力，支撑$2380，压力$2480"
        elif trend < -10:
            prediction = "近期回调，关注$2350支撑位，如守住可继续持有"
        else:
            prediction = "高位震荡为主，支撑$2380，压力$2480"
        gold['prediction'] = prediction
        
        print(f"  🥇 黄金: ${last:.2f} ({pct:+.2f}%) | ¥{cny_gold:.2f}/g")
    
    return gold

# ========== 持仓板块资金流 (Tushare) ==========
def load_plate_flows():
    """使用 Tushare 资金流接口"""
    plate_flows = []
    
    if TUSHARE_OK:
        # 获取沪深股通资金流
        df = tushare_get(PRO.moneyflow_hsgt)
        if df is not None and len(df) > 0:
            print(f"  💰 沪深港通资金流获取成功: {len(df)} 条")
            for _, row in df.head(3).iterrows():
                print(f"    {row['trade_date']} | 净流入: {row['net_hsgt']}万")
    
    # 东财板块资金流（备用）
    holdings = [
        ('008888', '华夏芯片ETF', '886052'),
        ('020274', '富国化工ETF', '886059'),
        ('022365', '永赢科技AI', '886031'),
        ('027048', '景顺AI机器人', '886541'),
        ('017223', '富国新能源电池', '886542'),
        ('290008', '泰信锂矿', '886054'),
    ]
    
    for fund_code, fund_name, plate_code in holdings:
        url = f"https://push2.eastmoney.com/api/qt/clist/get?fid=f62&op=1&fltt=2&invt=2&fs=b%3A{plate_code}&fields=f12,f14,f62,f184,f66,f69,f72&pn=1&pz=5&_={int(time.time())}"
        d = fetch_json(url)
        
        if d and d.get('data', {}).get('diff'):
            items = d['data']['diff']
            if items:
                item = items[0]
                main = item.get('f62', 0)
                org = item.get('f72', 0)
                big = item.get('f66', 0)
                retail = item.get('f184', 0)
                
                plate_flows.append({
                    'name': fund_name.replace('ETF', '').replace('基金', ''),
                    'funds': [fund_code],
                    '散户': int(retail),
                    '大户': int(big),
                    '机构': int(org),
                    '主力': int(main)
                })
                print(f"  💰 {fund_name}: 主力{int(main/10000):+,}万")
        
        time.sleep(0.3)
    
    return plate_flows

# ========== 热点板块 ==========
def load_plates():
    """加载热点板块"""
    plates = []
    
    watch_plates = [
        ('886052', '芯片半导体'),
        ('886083', 'CPO'),
        ('886041', 'PCB'),
        ('886541', '机器人'),
        ('886054', '锂矿'),
        ('886080', '创新药'),
        ('886542', '新能源电池'),
        ('886031', '科创创业AI'),
        ('886059', '细分化工'),
    ]
    
    for code, name in watch_plates:
        url = f"https://push2.eastmoney.com/api/qt/clist/get?fid=f3&op=1&fltt=2&invt=2&fs=b%3A{code}&fields=f2,f3,f12,f14,f62,f184&pn=1&pz=20&_={int(time.time())}"
        d = fetch_json(url)
        
        if d and d.get('data', {}).get('diff'):
            items = d['data']['diff']
            if items:
                total_chg = 0
                total_flow = 0
                count = 0
                
                for item in items[:10]:
                    chg = (item.get('f3', 0) or 0) / 100
                    flow = item.get('f62', 0) or 0
                    total_chg += chg
                    total_flow += flow
                    count += 1
                
                avg_chg = total_chg / count if count else 0
                
                plates.append({
                    'name': name,
                    'code': code,
                    'pct': round(avg_chg, 2),
                    'flow': int(total_flow),
                    'amount': round(total_flow / 100000000, 1)
                })
                flow_str = '流入' if total_flow > 0 else '流出'
                print(f"  🔥 {name}: {avg_chg:+.2f}% | {flow_str}{abs(total_flow/100000000):.1f}亿")
        
        time.sleep(0.2)
    
    return plates

# ========== 主程序 ==========
def main():
    print("=" * 50)
    print("📊 Market Monitor 数据更新")
    print(f"Tushare: {'✅ 已连接' if TUSHARE_OK else '❌ 未连接'}")
    print("=" * 50)
    
    data = load_existing()
    today = datetime.now().strftime('%Y-%m-%d')
    data['updated'] = today
    
    print("\n[1/4] 加载大盘指数...")
    data['indices'] = load_indices()
    
    print("\n[2/4] 加载黄金数据...")
    data['gold'] = load_gold()
    
    print("\n[3/4] 加载板块资金流...")
    data['plateFlows'] = load_plate_flows()
    
    print("\n[4/4] 加载热点板块...")
    data['plates'] = load_plates()
    
    save_data(data)
    
    print("\n" + "=" * 50)
    print(f"✅ 更新完成 {today}")
    print("=" * 50)

if __name__ == '__main__':
    main()
