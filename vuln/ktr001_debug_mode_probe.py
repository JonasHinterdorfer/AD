#!/usr/bin/env python3
import os, requests
BASE = os.getenv('TARGET', 'http://127.0.0.1:5000')
r = requests.get(f"{BASE}/this_route_should_not_exist", timeout=10)
print(r.status_code)
print(r.text[:800])
print('[*] If Werkzeug traceback/debugger appears, debug mode is exposed.')
