# Attack Guide: Auto Attack + Report GUI

This is your current battle setup: one attacker process + one dashboard process.

It now supports two scopes in one run:

1. Attack scope: enemy IPs, flags are submitted.
2. Defense scope: your own IPs, flags are only logged/reported and never submitted.

## 1. Components

Main attacker:

- AD/exploits/auto_attack.py

Monitoring GUI:

- AD/exploits/auto_attack_gui.py

Attack target list:

- AD/targets.txt

Defense target list:

- AD/defense_targets.txt

## 2. What Auto Attack Logs Every Minute

auto_attack.py writes structured data for analysis:

1. Per-exploit event logs with return code, duration, target, scope, service, vulnerability id, and retrieved flags.
2. Per-round reports (usually every minute) with:
   - attack fresh flags found
   - submitted vs failed counts
   - attack flags by vulnerability and target
   - defense retrievability by vulnerability and target
3. Cumulative metrics for total runs, total flags, top vulnerabilities, exploit health, and defense exposure.

Files produced:

1. AD/exploits/auto_attack.log (raw stdout/stderr of exploits)
2. AD/exploits/.cache/auto_attack_events.jsonl (event stream)
3. AD/exploits/.cache/minute_reports.jsonl (minute-by-minute report)
4. AD/exploits/.cache/auto_attack_metrics.json (aggregated dashboard metrics)
5. AD/exploits/.cache/auto_attack_seen_flags.json (attack dedupe cache)
6. AD/exploits/.cache/adaptive_timeouts.json (per-exploit adaptive timeout state)

Important:

- defense_retrieved_flags are never sent to submit API.

## 3. Start Commands

Install requirements once:

```powershell
cd AD/exploits
python -m pip install -r requirements.txt
```

Recommended: start both attacker + GUI from repo root (uses venv Python):

```powershell
cd C:\Users\Simon\Cyberleague
powershell -ExecutionPolicy Bypass -File .\run_auto_attack.ps1 -OpenBrowser
```

Manual start (attacker only):

```powershell
cd AD/exploits
C:/Users/Simon/Cyberleague/.venv/Scripts/python.exe auto_attack.py --targets-file ..\targets.txt --defense-targets-file ..\defense_targets.txt --submit-address http://localhost:8080 --submit-path /api/v1/flags --round-interval 60 --exploit-timeout 35 --timeout-overrides-file timeout_overrides.json --max-workers 32
```

Terminal 2: start GUI:

```powershell
cd AD/exploits
C:/Users/Simon/Cyberleague/.venv/Scripts/python.exe auto_attack_gui.py --host 127.0.0.1 --port 8090
```

Open in browser:

- http://127.0.0.1:8090

## 4. GUI Shows

Top cards:

1. Total exploit runs
2. Total new/retrieved flags
3. Total submitted flags (attack only)
4. Submit failures
5. Defense retrieved totals

Tables:

1. Top vulnerabilities by attack yield and defense retrievability
2. Exploit health (timeouts, return codes, yield)
3. Last minute reports with attack and defense vulnerability breakdowns

Recommendations block:

1. Exploits with high timeout rates
2. Exploits with many runs and no yield
3. Vulnerabilities still working on defense targets (patch priority)

## 5. Target File Formats

Edit AD/targets.txt:

```text
team01 10.10.10.1
team02 10.10.10.2
team03 10.10.10.3
```

Edit AD/defense_targets.txt:

```text
localhost 127.0.0.1
vulnbox 138.124.212.231
```

Any line text is fine; IPv4 addresses are extracted automatically.

## 6. Run Modes

All services with attack + defense checks:

```powershell
python auto_attack.py --targets-file ..\targets.txt --defense-targets-file ..\defense_targets.txt
```

Only one service:

```powershell
python auto_attack.py --targets-file ..\targets.txt --defense-targets-file ..\defense_targets.txt --only-service losnotes
```

Single test round:

```powershell
python auto_attack.py --targets-file ..\targets.txt --defense-targets-file ..\defense_targets.txt --once
```

Direct targets without files:

```powershell
python auto_attack.py --target 10.10.10.5 --defense-target 127.0.0.1 --defense-target 138.124.212.231
```

## 7. Patch Validation Workflow

Every 10-15 minutes:

1. Watch defense counters in GUI.
2. If a vulnerability still retrieves defense flags, patch is incomplete.
3. After patch rollout, verify defense retrievability for that vulnerability drops.
4. Keep high-yield attack vulnerabilities first in attack order.

Tuning knobs:

1. --exploit-timeout
2. --round-interval
3. --only-service
4. --submit-batch-size
5. --max-workers
6. --timeout-overrides-file
7. --adaptive-timeout-file
8. --adaptive-min-timeout
9. --adaptive-max-timeout
10. --adaptive-step-seconds
11. --no-adaptive-timeout

Adaptive timeout quick examples:

1. Use adaptive mode with custom bounds and step:

```powershell
python auto_attack.py --targets-file ..\targets.txt --defense-targets-file ..\defense_targets.txt --adaptive-min-timeout 15 --adaptive-max-timeout 120 --adaptive-step-seconds 5
```

2. Disable adaptive mode (use only base timeout + static overrides):

```powershell
python auto_attack.py --targets-file ..\targets.txt --defense-targets-file ..\defense_targets.txt --no-adaptive-timeout
```

3. Keep adaptive state in a custom file:

```powershell
python auto_attack.py --targets-file ..\targets.txt --defense-targets-file ..\defense_targets.txt --adaptive-timeout-file .cache\adaptive_timeouts_team10.json
```

## 8. Troubleshooting

No data in GUI:

1. Ensure auto_attack.py is running.
2. Check AD/exploits/.cache/auto_attack_metrics.json exists.
3. Ensure GUI is reading the same .cache directory.

Adaptive tuning not visible:

1. Confirm minute reports include adaptive_timeout_enabled and adaptive_tuning_events.
2. Check AD/exploits/.cache/adaptive_timeouts.json is being updated.
3. Ensure --no-adaptive-timeout is not set.

No attack submissions:

1. Confirm submit endpoint/path.
2. Confirm flag format CLA_[A-Za-z0-9/+]{32}.
3. Check minute_reports.jsonl submit_messages.

Defense still vulnerable:

1. Check GUI Defense Retrieved and per_vulnerability_defense_retrieved.
2. Patch corresponding service.
3. Re-run and verify defense counters decline.

## 9. Start-of-Round Checklist

1. Update AD/targets.txt with enemy IPs.
2. Update AD/defense_targets.txt with your defense IPs.
3. Start local defensive services in AD/srv.
4. Start auto_attack.py.
5. Start auto_attack_gui.py.
6. Confirm first minute report and first submissions.
7. Confirm defense checks run and are not submitted.

## 10. Stop and Resume

Stop:

1. Ctrl + C in both terminals.

Resume:

1. Start both commands again.

Seen-flag cache prevents duplicate attack resubmits; defense retrieval remains visible in logs/reports.
