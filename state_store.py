"""GitHub branch state: every save completes remotely before monitoring continues."""
import json
import os
import base64
from pathlib import Path
import httpx

def initial():
    return {'version': 1, 'days': {}, 'pending': []}

def validate(data):
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('days'), dict) or not isinstance(data.get('pending'), list):
        raise ValueError('状态文件损坏；停止发送，不能自动重置')
    return data

class LocalStore:
    def __init__(self, path): self.path = Path(path)
    def load(self):
        return validate(json.loads(self.path.read_text(encoding='utf-8'))) if self.path.exists() else initial()
    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.path)

class GithubStore:
    def __init__(self):
        self.base = 'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY']
        self.client = httpx.Client(timeout=30, headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
        self.sha = None
    def load(self):
        r = self.client.get(self.base + '/contents/state.json', params={'ref': 'monitor-state'})
        if r.status_code == 404 and os.getenv('BOOTSTRAP_STATE') == 'true':
            ref = self.client.get(self.base + '/git/ref/heads/monitor-state')
            if ref.status_code == 404:
                head = self.client.get(self.base + '/git/ref/heads/' + os.getenv('GITHUB_DEFAULT_BRANCH', 'main'))
                head.raise_for_status()
                created = self.client.post(self.base + '/git/refs', json={'ref': 'refs/heads/monitor-state', 'sha': head.json()['object']['sha']})
                created.raise_for_status()
            else: ref.raise_for_status()
            data = initial(); self.save(data); return data
        r.raise_for_status()
        obj = r.json(); self.sha = obj['sha']
        return validate(json.loads(base64.b64decode(obj['content'])))
    def save(self, data):
        payload = {'message': 'Persist monitor notification state', 'branch': 'monitor-state', 'content': base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()}
        if self.sha: payload['sha'] = self.sha
        r = self.client.put(self.base + '/contents/state.json', json=payload)
        r.raise_for_status(); self.sha = r.json()['content']['sha']
