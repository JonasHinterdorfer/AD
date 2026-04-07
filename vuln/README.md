# Exploit PoCs (AD/vuln)

Set target with env vars where applicable:
- `TARGET=http://127.0.0.1:5000`
- `USER`, `PASS`

## Cryze-Bank
- `cve001_timing_login.py`
- `cve002_lcg_predict.py`
- `cve003_aes_ctr_nonce_reuse.py`
- `cve004_plaintext_password_dump.py`
- `cve005_sqli_search.py`
- `cve006_wkhtmltopdf_lfi.py`
- `cve007_debug_lcg_leak.py`
- `cve008_stored_xss_poc.py`
- `cve009_csrf_transfer.html`

## KTorrent
- `ktr001_debug_mode_probe.py`
- `ktr002_ssti_404.py`
- `ktr003_tracker_csrf_poc.html`
- `ktr004_default_secret_cookie_forge.py`
- `ktr005_large_upload_dos.py`

PoCs are for authorized CTF use only.
