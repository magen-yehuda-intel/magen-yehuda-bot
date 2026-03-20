# TROUBLESHOOTING.md — Magen Yehuda Alert Monitor

Quick fixes for known issues. Check here before debugging from scratch.

---

## 🔴 Azure Table Storage — AuthorizationFailure

**Symptom:** Watcher log shows `AuthorizationFailure` on DB writes. Feed export may also fail.

**Cause:** Entra ID token expired. Tokens are acquired at watcher startup and not refreshed.

**Fix:** Restart the watcher:
```bash
cd ~/.openclaw/workspace/skills/iran-israel-alerts
bash ctl.sh stop && bash ctl.sh start
```

**Verify:** Check logs for successful DB writes:
```bash
tail -50 state/watcher.log | grep -i "db\|error\|auth"
```

**Note:** This was the same issue on Mar 19 (`export-feed.py`) and Mar 20 (watcher). Tokens expire silently — no warning before failure.

---

## 🔴 Duplicate Siren Alerts on Telegram

**Symptom:** Same siren wave produces 2-3 nearly identical Telegram messages.

**Cause (old):** Raw JSON string comparison — Oref sends slightly different area lists per poll cycle for the same wave.

**Fix (applied Mar 20):** Dedup now compares alert `id` fields instead of raw JSON. See `realtime-watcher.sh` line ~682.

**State files:**
- `state/watcher-oref-last.txt` — stores previous alert IDs

**Note:** There is NO cooldown timer. Each wave with a new `id` fires immediately. This is intentional — don't throttle legitimate new waves.

---

## 🔴 Missile Arc Animations Not Showing

**Symptom:** Dashboard loads but no missile arc animations appear.

**Possible causes:**
1. **Strike window filter:** Default is 24h. Old static events in `v2-data.js` won't show. Set to "All" to see historical arcs.
2. **No live events:** `live-events.json` is empty or doesn't exist. Check if watcher is running and classification fired.
3. **Animation toggle off:** Check if missile animation button is active (toolbar).

**Data flow:**
```
Oref sirens → classify-attack.py (GPT-5-mini) → write-live-event.py → docs/live-events.json → dashboard fetches every 30s → renderMissileArcs()
```

**Manual test:**
```bash
echo '{"source":"iran","weapon":"ballistic_missile","confidence":0.9,"direction":"multi","actor":"IRGC"}' | python3 scripts/write-live-event.py --oref-areas "Tel Aviv"
cat docs/live-events.json
```

**Classification requires:** Active Oref sirens + Azure OpenAI token (Entra ID). If token is expired, classification silently returns `{"source":"unknown"}` and no live event is written.

---

## 🟡 Watcher Dies / Orphaned Processes

**Symptom:** `ctl.sh status` shows watcher not running, or PID file points to dead process.

**Fix:**
```bash
bash ctl.sh stop    # kills by PID + cleans orphans
bash ctl.sh start   # fresh start
```

**Common causes:**
- Running watcher in exec subshell (SIGTERM on session end). Always use `ctl.sh`.
- macOS sleep/wake killing background processes.
- `--on2fatimeout=exit` flag (IB Gateway, not watcher — but same class of issue).

**Lesson:** After code changes to `realtime-watcher.sh`, always restart. Bash reads the script once at launch — a running PID won't have fixes.

---

## 🟡 Export Feed Fails (export-feed.py)

**Symptom:** Static JSON not updating, dashboard shows stale data.

**Check:**
```bash
# Cron running?
openclaw cron list | grep -i iran

# Manual run:
cd ~/.openclaw/workspace/skills/iran-israel-alerts
python3 scripts/export-feed.py
```

**Common cause:** Same Entra ID token expiry as above. Restart cron or re-run manually.

---

## 🟡 classify-attack.py Returns Unknown

**Symptom:** Watcher log shows classification but `source: unknown`.

**Causes:**
1. No Azure AD token (Entra ID expired) — check `az account get-access-token --resource https://cognitiveservices.azure.com`
2. No recent OSINT — `intel-log.jsonl` has no entries in last 15 minutes
3. Oref areas too vague — classification needs siren location data

**Debug:**
```bash
python3 scripts/classify-attack.py --oref-areas "Tel Aviv,Jerusalem,Haifa"
```

---

## 🟢 Dashboard Labels Confusing

| Old Label | Current Label | Hebrew Meaning |
|-----------|--------------|----------------|
| ℹ️ Stand Down | ⏹ Alert Ended | ביטול התרעה |
| ✅ All Clear | ✅ All Clear | הכל בסדר |
| 🚨 Rockets & Missiles | 🚨 Rockets & Missiles | ירי רקטות וטילים |

---

## Running Tests

```bash
# Python tests (live event pipeline)
python3 tests/test-live-events.py -v

# Node tests (dashboard JS logic)
node tests/test-centcom-node.js

# Browser tests (visual)
open tests/test-centcom-dashboard.html
```

---

## Key State Files

| File | Purpose |
|------|---------|
| `state/watcher.pid` | Current watcher PID |
| `state/watcher.log` | Watcher output log |
| `state/watcher-oref-last.txt` | Last Oref alert IDs (dedup) |
| `state/watcher-threat-level.txt` | Current threat level (persists across restarts) |
| `state/intel-log.jsonl` | All OSINT events |
| `state/dispatch-log.jsonl` | Telegram dispatch history |
| `docs/live-events.json` | Live missile events for dashboard arcs |

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `API_URL/api/oref` | Live Oref siren data |
| `API_URL/api/oref/history?limit=5` | Siren history (dashboard panel) |
| `API_URL/api/push/threat` | Push threat level + classification |
| `API_URL/api/live-events` | Live missile events (if API supports it) |
| `docs/live-events.json` | Static fallback for live events |
