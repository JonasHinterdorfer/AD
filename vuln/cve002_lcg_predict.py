#!/usr/bin/env python3
import os, requests

BASE = os.getenv('TARGET', 'http://127.0.0.1:5000')
USER = os.getenv('USER', 'user')
PASS = os.getenv('PASS', 'pass')

s = requests.Session()
s.post(f"{BASE}/login", data={'username': USER, 'password': PASS}, timeout=10)
r = s.get(f"{BASE}/api/v1/debug/lcg", timeout=10)
leak = r.json()
print('[+] leaked 2 outputs:', leak)
print('[*] Use leak to recover LCG state/params and predict randfunc stream for RSA prime generation.')
