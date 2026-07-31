#!/usr/bin/env python3
"""
通过 GitHub API 更新 api/data.json
绕过 GITHUB_TOKEN 无法 git push 的限制
"""
import json
import base64
import urllib.request
import os
import datetime

def api(method, path, data=None):
    token = os.environ.get('GITHUB_TOKEN', '')
    repo = os.environ.get('REPO', 'xiaoliu-bot/market-monitor')
    url = f"https://api.github.com{path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    if data:
        body = json.dumps(data).encode('utf-8')
        req.data = body
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'error': e.read().decode('utf-8', errors='replace'), 'code': e.code}

def push_file(repo, file_path, content, message):
    """通过 GitHub API 写入文件"""
    # 获取当前 SHA
    result = api('GET', f'/repos/{repo}/contents/{file_path}')
    sha = result.get('sha') if 'sha' in result else None
    
    # 写入
    payload = {
        'message': message,
        'content': base64.b64encode(content.encode('utf-8')).decode('ascii'),
    }
    if sha:
        payload['sha'] = sha
    
    result = api('PUT', f'/repos/{repo}/contents/{file_path}', payload)
    if 'error' in result:
        print(f"  ❌ {file_path}: {result['error']}")
        return False
    print(f"  ✅ {file_path}: {result['content']['sha'][:8]}")
    return True

def main():
    repo = os.environ.get('REPO', 'xiaoliu-bot/market-monitor')
    print(f"仓库: {repo}")
    
    # 1. 读取抓取的数据
    if os.path.exists('api/data.json'):
        with open('api/data.json', 'r', encoding='utf-8') as f:
            data_content = f.read()
        msg = f"📊 收盘数据 {datetime.date.today().strftime('%Y-%m-%d')}"
        ok = push_file(repo, 'api/data.json', data_content, msg)
        
        # 2. 同时保存历史
        today = datetime.date.today().strftime('%Y-%m-%d')
        if os.path.exists(f'api/history/{today}.json'):
            with open(f'api/history/{today}.json', 'r', encoding='utf-8') as f:
                hist = f.read()
            push_file(repo, f'api/history/{today}.json', hist, f"📁 历史快照 {today}")
    else:
        print("❌ api/data.json 未找到")
        exit(1)

if __name__ == '__main__':
    main()
