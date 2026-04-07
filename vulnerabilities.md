# CTF Services Vulnerability Index

## Overview
This document contains all identified vulnerabilities across three CTF services: CryzeBank, KTorrent, and LosNotes. Each vulnerability is categorized by service and severity level for easy reference during attack planning and patching.

---

## CRYZE-BANK Service

### CVE-001: Authentication Timing Attack (HIGH)
**Location:** [src/server.py](src/server.py#L57-L68)  
**Type:** Timing Side-Channel Attack  
**Severity:** HIGH  
**CVSS:** 7.5

**Description:**
The login endpoint implements a character-by-character password comparison with a deliberate 20ms sleep for each correct character match. This creates a measurable timing difference that allows attackers to determine correct password characters sequentially.

**Vulnerable Code:**
```python
for i, char in enumerate(password):
    if char == user.password[i]:
        time.sleep(0.02)  # 20ms delay for correct characters
    else:
        access = False
        break
```

**Attack Vector:**
- Measure response time for each login attempt
- Characters with longer response times are correct
- Brute force password character-by-character
- Average password can be cracked in minutes

**Impact:** Complete authentication bypass for any user account

**Status:** NOT PATCHED

---

### CVE-002: Weak Cryptography - Linear Congruential Generator (CRITICAL)
**Location:** [src/crypto_utils.py](src/crypto_utils.py#L1-L30)  
**Type:** Cryptographic Weakness  
**Severity:** CRITICAL  
**CVSS:** 9.1

**Description:**
RSA encryption uses a weak Linear Congruential Generator (LCG) instead of a cryptographically secure random number generator. The LCG parameters are exposed via the debug endpoint, allowing complete prediction of "random" prime generation.

**Vulnerable Code:**
```python
GLOBAL_M = 2**19 - 1
GLOBAL_A = random.randint(1, 2**19) 
GLOBAL_C = random.randint(1, 2**19)

def LCG():
    seed = random.randint(0, GLOBAL_M - 1)
    def randfunc(num_bytes):
        nonlocal seed 
        seed = (GLOBAL_A * seed + GLOBAL_C) % GLOBAL_M
        expanded = (seed * 0x85ebca6b) % (2**32)
        result.extend(expanded.to_bytes(4, 'big'))
```

**Attack Vector:**
- Call `/api/v1/debug/lcg` endpoint to leak internal state
- Use leaked state to predict all future random bytes
- Predict RSA prime generation
- Factor RSA moduli (for 1024-bit primes)
- Decrypt all RSA-encrypted messages

**Impact:** Complete RSA encryption bypass, ability to decrypt all encrypted transactions

**Notes:** 
- LCG is suitable for simulation but NOT for cryptography
- Period is limited to 2^19
- Expandable via hardcoded multiplier (0x85ebca6b)

**Status:** NOT PATCHED

---

### CVE-003: Hardcoded Nonce in AES-CTR (HIGH)
**Location:** [src/server.py](src/server.py#L18)  
**Type:** Cryptographic Weakness  
**Severity:** HIGH  
**CVSS:** 8.1

**Description:**
AES-CTR mode uses a hardcoded nonce value (`\x13\37\x13\37` repeated twice) for all encrypted messages. Reusing the same nonce with the same key allows keystream recovery and message decryption.

**Vulnerable Code:**
```python
KEY = secrets.token_bytes(32)
NONCE = b"\x13\x37\x13\x37"*2  # Hardcoded, never changes

def aes_encrypt(msg, key, nonce):
    aes = AES.new(key, AES.MODE_CTR, nonce=nonce)
    return aes.encrypt(pad(msg.encode(), 16)).hex()
```

**Attack Vector:**
- Collect multiple AES-encrypted messages
- XOR ciphertexts together to cancel keystream
- Recover keystream and plaintext messages
- Decrypt transaction messages

**Impact:** All AES-encrypted transaction messages can be recovered

**Status:** NOT PATCHED

---

### CVE-004: Plaintext Password Storage (CRITICAL)
**Location:** [src/models.py](src/models.py#L11), [src/server.py](src/server.py#L100-L101)  
**Type:** Sensitive Data Exposure  
**Severity:** CRITICAL  
**CVSS:** 9.8

**Description:**
User passwords are stored in plaintext in the database. There is no password hashing, salting, or any cryptographic protection.

**Vulnerable Code:**
```python
class User(UserMixin, db.Model):
    password = db.Column(db.String, nullable=False)

# Registration:
db.session.add(User(username=username, password=password))  # Direct plaintext storage
```

**Attack Vector:**
- Gain database access (via SQL injection, backup theft, etc.)
- Read passwords directly from database
- Use passwords for lateral movement and account takeover

**Impact:** Complete compromise of all user accounts

**Status:** NOT PATCHED

---

### CVE-005: SQL Injection in Transaction Search (CRITICAL)
**Location:** [src/server.py](src/server.py#L327-L340)  
**Type:** SQL Injection  
**Severity:** CRITICAL  
**CVSS:** 9.9

**Description:**
The transaction search endpoint constructs SQL queries by concatenating unsanitized user input. The `q` parameter is directly interpolated into the SQL query.

**Vulnerable Code:**
```python
@app.route('/api/v1/transactions/search')
@login_required
def search_transactions():
    q = request.args.get('q', '')
    query = f"SELECT ... FROM transactions WHERE username = '{current_user.username}' AND recipient LIKE '%{q}%'"
    results = db.session.execute(db.text(query))
```

**Attack Vector:**
```
GET /api/v1/transactions/search?q=' OR '1'='1
GET /api/v1/transactions/search?q=%' UNION SELECT id,password,email FROM users WHERE id LIKE '%
GET /api/v1/transactions/search?q=%'; DROP TABLE transactions; --
```

**Impact:** 
- Data exfiltration (read all transactions, user data)
- Data modification (alter transaction records)
- Data deletion
- Remote code execution (database-dependent)

**Status:** NOT PATCHED

---

### CVE-006: Command Injection via PDF Export (HIGH)
**Location:** [src/server.py](src/server.py#L189-L209)  
**Type:** Command Injection  
**Severity:** HIGH  
**CVSS:** 8.8

**Description:**
The PDF export functionality renders HTML and pipes it directly to wkhtmltopdf via subprocess. While the direct input is from `render_template()`, transaction data (recipient, amount, message) can contain arbitrary strings that may be interpreted by wkhtmltopdf.

**Vulnerable Code:**
```python
def export_transactions_pdf():
    transactions_html = render_template('transactions.html', ...)
    pdf_process = subprocess.run(
        ['wkhtmltopdf', '--quiet', '-', '-'],
        input=transactions_html.encode('utf-8'),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
```

**Attack Vector:**
- Create transaction with malicious recipient or message containing wkhtmltopdf directives
- When export is triggered, parse the embedded commands
- Potential for file read/write via wkhtmltopdf plugins

**Impact:** Information disclosure, local file read (if wkhtmltopdf plugins enabled)

**Status:** NOT PATCHED

---

### CVE-007: Debug Endpoint Information Disclosure (HIGH)
**Location:** [src/server.py](src/server.py#L315-L320)  
**Type:** Information Disclosure  
**Severity:** HIGH  
**CVSS:** 7.5

**Description:**
Debug endpoint `/api/v1/debug/lcg` exposes the internal state of the LCG random number generator generating internal state leakage that breaks CVE-002.

**Vulnerable Code:**
```python
@app.route('/api/v1/debug/lcg')
@login_required
def lcg_route():
    lcg_gen = LCG()
    random_bytes = lcg_gen(8)
    return [bytes_to_long(random_bytes[:4]), bytes_to_long(random_bytes[4:])]
```

**Attack Vector:**
- Call endpoint (requires any valid login)
- Obtain LCG internal state
- Predict all future "random" values
- Predict RSA primes

**Impact:** Enables cryptographic attacks (see CVE-002)

**Status:** NOT PATCHED

---

### CVE-008: Potential XSS via Safe Filter Misuse (MEDIUM)
**Location:** [src/templates/dashboard.html](src/templates/dashboard.html#L50-L52), [src/templates/transaction.html](src/templates/transaction.html#L37)  
**Type:** Cross-Site Scripting (XSS)  
**Severity:** MEDIUM  
**CVSS:** 6.1

**Description:**
Templates use Jinja2's `| safe` filter with user-controlled data. While transaction recipient and amount appear to be validated, the use of `| safe` bypasses auto-escaping for fields that store transaction metadata.

**Vulnerable Code:**
```html
<td>{{ tx.created_at | safe }}</td>
<td>{{ tx.recipient }}</td>
<td>{{ tx.amount | safe }}€</td>
```

**Attack Vector:**
- Create transaction with special characters in `created_at` or `amount`
- If validation is inadequate, inject JavaScript through stored XSS
- Steal session cookies or perform CSRF attacks

**Impact:** Session hijacking, account takeover, malware distribution

**Status:** LOW PRIORITY (requires multiple conditions)

---

### CVE-009: No CSRF Protection (MEDIUM)
**Location:** [src/server.py](src/server.py)  
**Type:** Cross-Site Request Forgery  
**Severity:** MEDIUM  
**CVSS:** 6.5

**Description:**
Flask app is configured without CSRF protection. No CSRF tokens are used in forms for state-changing operations like transfers and profile updates.

**Attack Vector:**
```html
<!-- Attacker's site -->
<form action="http://victim-app/transfer" method="POST">
    <input name="recipient" value="attacker">
    <input name="amount" value="99999">
    <input type="submit" value="Click here">
</form>
```

**Impact:** Unauthorized transfers, account modifications

**Status:** NOT PATCHED

---

---

## KTORRENT Service

### KTR-001: Flask Debug Mode Enabled in Production (HIGH)
**Location:** [src/app.py](src/app.py#L57)  
**Type:** Insecure Configuration  
**Severity:** HIGH  
**CVSS:** 8.1

**Description:**
Flask application runs with `debug=True` in production. This enables the interactive debugger and reloader, exposing sensitive information and allowing arbitrary code execution.

**Vulnerable Code:**
```python
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
```

**Attack Vector:**
- Access `/` and trigger an error to open debugger
- Inspect application state, environment variables
- Interactive console access (if PIN guessed or bypassed)
- Remote code execution

**Impact:** Complete system compromise, remote code execution

**Status:** NOT PATCHED

---

### KTR-002: Jinja2 Template Injection in 404 Handler (CRITICAL)
**Location:** [src/app.py](src/app.py#L44-L47)  
**Type:** Server-Side Template Injection  
**Severity:** CRITICAL  
**CVSS:** 9.8

**Description:**
The 404 error handler uses `render_template_string()` with unsanitized user input from the request path.

**Vulnerable Code:**
```python
@app.errorhandler(404)
def page_not_found(e):
    return render_template_string(
        f'<h1>404 Not Found</h1><p>The page <code>{flask_request.path}</code> does not exist.</p>'
    ), 404
```

**Attack Vector:**
```
GET /{{7*7}}  → Shows 49 in response
GET /{{request.environ}}  → Exposes all environment variables
GET /{{config}}  → Exposes app config including SECRET_KEY
GET /{{__import__('os').popen('id').read()}}  → Remote code execution
```

**Impact:** Complete remote code execution, environment variable exfiltration

**Status:** NOT PATCHED

---

### KTR-003: CSRF Protection Disabled for Tracker (MEDIUM)
**Location:** [src/app.py](src/app.py#L25)  
**Type:** Cross-Site Request Forgery  
**Severity:** MEDIUM  
**CVSS:** 6.5

**Description:**
CSRF protection is explicitly disabled for the tracker blueprint, allowing any site to make announce requests on behalf of users.

**Vulnerable Code:**
```python
csrf.init_app(app)
# ...
csrf.exempt(tracker_bp)  # CSRF protection disabled
```

**Attack Vector:**
- Craft malicious page with hidden tracker announce request
- When user visits, it modifies their torrent announce stats
- Could be used to manipulate peer information

**Impact:** Tracker state manipulation, peer list corruption

**Status:** NOT PATCHED

---

### KTR-004: Weak Default Secret Key (MEDIUM)
**Location:** [src/config.py](src/config.py#L4)  
**Type:** Insecure Configuration  
**Severity:** MEDIUM  
**CVSS:** 6.1

**Description:**
Configuration contains a hardcoded default secret key for development that is weak and publicly visible.

**Vulnerable Code:**
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
```

**Attack Vector:**
- If environment variable not set, default weak key is used
- Allows session token forgery
- Prototype pollution attacks

**Impact:** Session hijacking, session token forgery

**Status:** PARTIALLY PATCHED (requires proper env var setup)

---

### KTR-005: Excessive File Upload Size (LOW)
**Location:** [src/config.py](src/config.py#L9)  
**Type:** Denial of Service / Resource Exhaustion  
**Severity:** LOW  
**CVSS:** 5.3

**Description:**
Maximum upload size is set to 500MB without proper disk space validation or rate limiting.

**Attack Vector:**
- Upload multiple large files
- Exhaust disk space
- Cause application outage

**Impact:** Denial of service via disk space exhaustion

**Status:** NOT PATCHED

---

---

## LOSNOTES Service

### LN-001: Plaintext Password Storage (CRITICAL)
**Location:** [losnotes/models/user.py](losnotes/models/user.py#L14)  
**Type:** Sensitive Data Exposure  
**Severity:** CRITICAL  
**CVSS:** 9.8

**Description:**
User passwords are stored as plaintext in the PostgreSQL database with no hashing, salting, or encryption.

**Vulnerable Code:**
```python
class User(flask_login.UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))  # Plaintext!
    
    @classmethod
    def add(cls, email: str, password: str):
        user = cls(email=email, password=password)  # Direct plaintext storage
```

**Attack Vector:**
- Gain database access
- Read password column directly
- Use credentials for login or lateral movement

**Impact:** Complete user account compromise

**Status:** NOT PATCHED

---

### LN-002: Hardcoded Database Credentials (CRITICAL)
**Location:** [losnotes/_main.py](losnotes/_main.py#L22-L23)  
**Type:** Sensitive Data Exposure  
**Severity:** CRITICAL  
**CVSS:** 9.1

**Description:**
Database credentials are hardcoded in the application source code.

**Vulnerable Code:**
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:froth_area_jot_rendition_buckwheat_rematch@losnotes-postgresql:5432/notes_db'
```

**Credentials:**
- User: `postgres`
- Password: `froth_area_jot_rendition_buckwheat_rematch`
- Host: `losnotes-postgresql`
- Database: `notes_db`

**Attack Vector:**
- Access source code (repository, container image, backup)
- Connect directly to database
- Read/modify/delete all user data

**Impact:** Complete database compromise

**Status:** NOT PATCHED

---

### LN-003: Flask Debug Mode Enabled (HIGH)
**Location:** [losnotes/_main.py](losnotes/_main.py#L44)  
**Type:** Insecure Configuration  
**Severity:** HIGH  
**CVSS:** 8.1

**Description:**
Application runs with `debug=True` in production, enabling the interactive debugger and hot reloader.

**Vulnerable Code:**
```python
app.run(host="0.0.0.0", port=8080, debug=True)
```

**Attack Vector:**
- Trigger application error
- Access interactive debugger console
- Execute arbitrary Python code
- Access application state and environment

**Impact:** Remote code execution

**Status:** NOT PATCHED

---

### LN-004: User ID Injection in API Key Creation (HIGH)
**Location:** [losnotes/routes/api.py](losnotes/routes/api.py#L17-L27)  
**Type:** Privilege Escalation / Authorization Bypass  
**Severity:** HIGH  
**CVSS:** 8.2

**Description:**
The create API key endpoint accepts a user-supplied `user_id` parameter, allowing authenticated users to create API keys for other users.

**Vulnerable Code:**
```python
@api_blueprint.route("/api/keys", methods=["POST"])
@flask_login.login_required
def create_api_key():
    data = flask.request.get_json(silent=True) or {}
    user_id = data.get('user_id', flask_login.current_user.id)  # User controls user_id!
    api_key = models.api_key.ApiKey.add(user_id=user_id)
```

**Attack Vector:**
```bash
curl -X POST http://app/api/keys \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2}'  # Create key for user ID 2
```

**Impact:** 
- Create API keys for other users
- Access other users' notes via API
- Impersonate other users' API access

**Status:** NOT PATCHED

---

### LN-005: Missing Authentication on Raw Note Endpoint (CRITICAL)
**Location:** [losnotes/routes/dashboard.py](losnotes/routes/dashboard.py#L55-L71)  
**Type:** Authentication Bypass / Authorization Bypass  
**Severity:** CRITICAL  
**CVSS:** 9.1

**Description:**
The `/raw/<note_id>` endpoint has login_required commented out with a comment suggesting that security relies only on ID guessing. This allows unauthenticated access to any note if its ID is known.

**Vulnerable Code:**
```python
@dashboard_blueprint.route("/raw/<int:note_id>", methods=["GET"])
# TODO: This caused an issue in production (see JIRA-512)
# As long as no one guesses the user_id and the note_id, everything should be fine
# @flask_login.login_required  # COMMENTED OUT!
def dashboard_raw_get_route(note_id):
    note = models.notes_entry.NotesEntry.query.filter_by(
        id=note_id
    ).filter_by(
        deleted=False
    ).first()
    
    if not note:
        return "Note not found!"
    
    return note.note
```

**Attack Vector:**
- Enumerate note IDs (typically sequential integers)
- Access notes without authentication
- Extract sensitive information stored in notes

**Impact:** 
- Information disclosure
- Notes contain passwords, API keys, secrets based on app name

**Status:** NOT PATCHED

---

### LN-006: SQL Injection in Note Search (MEDIUM)
**Location:** [losnotes/routes/dashboard.py](losnotes/routes/dashboard.py#L35-L48)  
**Type:** SQL Injection  
**Severity:** MEDIUM  
**CVSS:** 6.5

**Description:**
The note search endpoint uses SQLAlchemy's `like()` method with user-supplied search text. While SQLAlchemy parameterizes the query, LIKE wildcards in user input can cause issues.

**Vulnerable Code:**
```python
@dashboard_blueprint.route("/search_note", methods=["POST"])
@flask_login.login_required
def dashboard_search_password_post_route():
    search_text = flask.request.form.get('search')
    notes = [
        [entry.note, entry.id, entry.user_id]
        for entry in models.notes_entry.NotesEntry.query.filter(
            models.notes_entry.NotesEntry.note.like(f"%{search_text}%")  # User controls search_text
        )
    ]
```

**Attack Vector:**
```
Search: %
Result: All notes retrieved (bypass search)

Search: %' UNION SELECT ... --
Result: Potential injection depending on ORM internals
```

**Impact:** 
- Unintended data disclosure
- Potential for advanced SQL injection depending on SQLAlchemy version

**Status:** PARTIAL RISK (SQLAlchemy provides some protection)

---

### LN-007: Remember Me Token Risk (MEDIUM)
**Location:** [losnotes/routes/auth.py](losnotes/routes/auth.py#L33)  
**Type:** Weak Session Management  
**Severity:** MEDIUM  
**CVSS:** 5.9

**Description:**
The login function uses `remember=True` flag without configurable remember duration, and Flask-Login's default remember token is weak.

**Vulnerable Code:**
```python
def login_post_route():
    # ...
    flask_login.login_user(user, remember=True)  # Remember forever with weak token
```

**Attack Vector:**
- Steal remember me cookie from network traffic
- Use cookie to impersonate user indefinitely
- Weak token generation in Flask-Login (especially in older versions)

**Impact:** Session hijacking, long-term account compromise

**Status:** PARTIALLY MITIGATED (depends on Flask-Login version)

---

---

## Patching Priority Matrix

### CRITICAL (Patch Immediately)
1. **CVE-002** (CryzeBank) - LCG weakness - Breaks all cryptography
2. **CVE-004** (CryzeBank) - Plaintext passwords
3. **CVE-005** (CryzeBank) - SQL injection
4. **KTR-002** (KTorrent) - Template injection - RCE
5. **LN-001** (LosNotes) - Plaintext passwords
6. **LN-002** (LosNotes) - Hardcoded credentials
7. **LN-005** (LosNotes) - Authentication bypass

### HIGH (Patch Soon)
1. **CVE-001** (CryzeBank) - Timing attack
2. **CVE-003** (CryzeBank) - Hardcoded nonce
3. **CVE-006** (CryzeBank) - Command injection
4. **CVE-007** (CryzeBank) - Debug endpoint
5. **KTR-001** (KTorrent) - Debug mode
6. **LN-003** (LosNotes) - Debug mode
7. **LN-004** (LosNotes) - User ID injection

### MEDIUM (Schedule Patching)
1. **CVE-008** (CryzeBank) - XSS via safe filter
2. **CVE-009** (CryzeBank) - CSRF protection
3. **KTR-003** (KTorrent) - CSRF exemption
4. **KTR-004** (KTorrent) - Weak secret key
5. **LN-006** (LosNotes) - SQL injection risk
6. **LN-007** (LosNotes) - Remember me token

### LOW (Consider Hardening)
1. **KTR-005** (KTorrent) - Large file uploads

---

## Exploitation Notes

### Quick Wins for Immediate Attack
1. Create account and call `/api/v1/debug/lcg` to leak LCG state
2. Enumerate note IDs on LosNotes and access `/raw/<id>` without login
3. Create API key for another user on LosNotes
4. Trigger 404 on KTorrent and inject template

### Complex Exploitation Chains
1. **CryzeBank Complete Compromise:**
   - Use timing attack to brute-force admin password
   - Login as admin
   - Use SQL injection to read all transactions
   - Decrypt RSA messages using leaked LCG state
   - Create high-value transfer with XSS payload in recipient field

2. **LosNotes Account Takeover:**
   - Enumerate note IDs (1, 2, 3, ...)
   - Read notes via `/raw/<id>` (likely contain passwords)
   - Use credentials to login as other users
   - Create API keys for persistence

3. **KTorrent RCE:**
   - Visit `/{{__import__('os').popen('cat%20/etc/passwd').read()}}`
   - Gain instant RCE
   - Read database or environment

---

## Notes for Patching
- **CryzeBank**: Requires complete cryptographic redesign
- **KTorrent**: Quick fixes available (disable debug, CSRF fix)
- **LosNotes**: Password hashing essential, environment variables for credentials
