import os, json, base64, urllib.request, urllib.error, sys, time
from concurrent.futures import ThreadPoolExecutor

TOKEN = os.environ['GH_TOKEN']
OWNER, REPO = 'hemu996', 'smart-ppt-designer'
BRANCH = 'main'
API = 'https://api.github.com'

def req(method, path, payload=None):
    url = API + path
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header('Authorization', 'Bearer ' + TOKEN)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('Content-Type', 'application/json')
    for attempt in range(5):
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                body = resp.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (404, 429, 502, 503, 504) and attempt < 5:
                time.sleep(2 + attempt*2); continue
            raise RuntimeError(f'{method} {path} -> {e.code}: {detail}')
        except Exception as ex:
            if attempt < 5:
                time.sleep(2 + attempt*2); continue
            raise

# 收集文件（遵循 .gitignore 的核心排除项）
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'output'}
SKIP_EXT = {'.pyc', '.log'}
files = []
for root, dirs, names in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for n in names:
        if os.path.splitext(n)[1].lower() in SKIP_EXT: continue
        p = os.path.join(root, n).replace('\\', '/')
        if p.startswith('./'): p = p[2:]
        fsize = os.path.getsize(p)
        if fsize > 40*1024*1024:
            print('SKIP big', p, fsize); continue
        files.append((p, fsize))
files.sort()
print(f'files: {len(files)}')

# 1) 逐个上传 blob（串行 + 退避重试，避开并发限流）
def make_blob(item):
    p, _ = item
    with open(p, 'rb') as f:
        content = base64.b64encode(f.read()).decode()
    r = req('POST', f'/repos/{OWNER}/{REPO}/git/blobs', {'content': content, 'encoding': 'base64'})
    return p, r['sha']

t0 = time.time()
tree_entries = []
for i, item in enumerate(files, 1):
    p, sha = make_blob(item)
    tree_entries.append({'path': p, 'mode': '100644', 'type': 'blob', 'sha': sha})
    if i % 10 == 0:
        print(f'  blobs {i}/{len(files)}  {round(time.time()-t0)}s', flush=True)
print(f'blobs done: {len(tree_entries)} in {round(time.time()-t0)}s')

# 2) tree
tree = req('POST', f'/repos/{OWNER}/{REPO}/git/trees', {'tree': tree_entries})
print('tree:', tree['sha'][:12])

# 3) 以已有提交为 parent
ref = req('GET', f'/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}')
parent = ref['object']['sha']
print('parent:', parent[:12])
msg = open('_commitmsg.txt', encoding='utf-8').read()
commit = req('POST', f'/repos/{OWNER}/{REPO}/git/commits',
             {'message': msg, 'tree': tree['sha'], 'parents': [parent]})
print('commit:', commit['sha'][:12])

# 4) 更新分支 ref（force，避免 non-fast-forward）
req('PATCH', f'/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}',
    {'sha': commit['sha'], 'force': True})
print('ref updated:', BRANCH)
print('DONE')
