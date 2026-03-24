#!/usr/bin/env python3
"""
generate-brief.py — Generate LLM-powered intel briefs (EN + HE) from recent events.
Runs every 30 min via cron. Reads intel-log.jsonl, calls gpt-5-mini, writes docs/brief.json.

Output format: { "generated_at": ISO, "briefs": { "0.5": {"en":..,"he":..}, "2": {...}, ... } }
"""

import json, os, sys, time, urllib.request
from datetime import datetime, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
INTEL_LOG = os.path.join(ROOT, "state", "intel-log.jsonl")
INTEL_FEED = os.path.join(ROOT, "docs", "intel-feed.json")
OUTPUT = os.path.join(ROOT, "docs", "brief.json")

AOAI_ENDPOINT = os.environ.get("AOAI_ENDPOINT", "https://openai-dev-nt6mukageprxm.openai.azure.com")
AOAI_DEPLOYMENT = os.environ.get("AOAI_DEPLOYMENT", "gpt-5-mini")
AOAI_API_VERSION = "2025-01-01-preview"

TIME_WINDOWS = [0.5, 2, 6, 24, 48]  # hours

def _get_token():
    try:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    except Exception as e:
        print(f"Auth failed: {e}", file=sys.stderr)
        sys.exit(1)

def load_events(max_hours=48):
    """Load events from intel-log.jsonl + intel-feed.json within the last max_hours."""
    cutoff = time.time() - (max_hours * 3600)
    events = []

    # Load from intel-log.jsonl
    try:
        with open(INTEL_LOG, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    ts = ev.get("ts") or ev.get("logged_at") or 0
                    if ts >= cutoff:
                        ev["_ts"] = ts
                        events.append(ev)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"No intel log at {INTEL_LOG}", file=sys.stderr)

    # Load from intel-feed.json (OSINT events with actual text)
    seen_texts = set()
    try:
        with open(INTEL_FEED, "r") as f:
            feed = json.load(f)
        feed_events = feed if isinstance(feed, list) else feed.get("events", feed.get("data", []))
        for ev in feed_events:
            ts = ev.get("ts", 0)
            if ts < cutoff:
                continue
            text = (ev.get("notes") or ev.get("text") or "").strip()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)
            events.append({
                "_ts": ts,
                "type": "osint",
                "src": ev.get("src", ev.get("source", "")),
                "text": text,
                "loc": ev.get("location", ev.get("loc", "")),
                "side": ev.get("side", ""),
            })
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not load intel-feed.json: {e}", file=sys.stderr)

    return sorted(events, key=lambda e: e.get("_ts", 0), reverse=True)

def filter_events(events, hours):
    cutoff = time.time() - (hours * 3600)
    return [e for e in events if e.get("_ts", 0) >= cutoff]

def events_to_text(events, max_chars=5000):
    """Convert events to compact text for LLM prompt."""
    lines = []
    for e in events:
        ts = e.get("_ts", 0)
        t = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M") if ts else "??:??"
        src = e.get("src", "") or e.get("source", "") or e.get("type", "")
        loc = e.get("loc", "") or e.get("location", "")
        text = (e.get("text", "") or e.get("summary", "") or "").strip()[:200]
        
        # For flight_scan events, build a summary
        if e.get("type") == "flight_scan" and e.get("data"):
            d = e["data"]
            text = f"Flight scan: {d.get('total',0)} aircraft, {d.get('military_count',0)} military ({', '.join(d.get('military_callsigns',[])[:3])})"
            if d.get('airports_closed'):
                text += f", airports closed: {', '.join(d['airports_closed'])}"
        
        # For cyber_scan events
        if e.get("type") == "cyber_scan":
            text = f"Cyber scan: {e.get('count',0)} incidents, severity {e.get('severity','?')}"

        # Skip if no meaningful text
        if not text:
            continue

        cat = e.get("cat", "")
        line = f"[{t}] {src}: {text}"
        if loc:
            line += f" ({loc})"
        if cat:
            line += f" [{cat}]"
        lines.append(line)
    result = "\n".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... (truncated)"
    return result

SYSTEM_PROMPT = """You are a military intelligence briefing officer writing a situation report for Israeli civilians monitoring the Iran-Israel conflict.

RULES:
- Be DIRECT and CONCISE. No fluff. No filler. No "it's important to note".
- Lead with what matters: attacks, military movements, political developments.
- Cut the noise: skip duplicate reports, minor social media chatter, unverified rumors.
- Group related events into themes (e.g. "Northern Border", "Hormuz", "Diplomacy").
- Add brief tactical context where useful (e.g. "first time X was used", "3rd attack this week").
- Use bullet points. Short sentences. Every word earns its place.
- If there are active sirens or strikes — that goes FIRST, bold.

INTERNATIONAL & GOOD NEWS:
- Include interesting international reactions ONLY if they involve real action (troops moved, sanctions imposed, embargoes, ports closed, emergency sessions). Skip generic "country X condemns" statements.
- European/global news only if genuinely surprising or impactful (e.g. Germany deploys Patriot, Turkey closes strait, oil price shock).
- Do NOT include every politician's opinion or statement. Nobody cares that "French FM expressed concern".
- Actively look for GOOD NEWS: successful interceptions, humanitarian aid arriving, ceasefire talks progressing, civilians rescued, international support with teeth. People need hope too.
- End with a "🟢 Good News" bullet if anything positive happened (even small wins).

BOTTOM LINE:
- End with a 1-line threat assessment (escalating/stable/de-escalating).

FORMAT:
Return a JSON object with two keys:
- "en": English brief (HTML, use <b>, <ul>, <li>, <h3> tags)
- "he": Hebrew brief (HTML, RTL, same content translated naturally — not robotic translation, write like a Hebrew news anchor)

Keep each brief under 300 words. Quality over quantity."""

USER_PROMPT_TEMPLATE = """CONTEXT: This is Day 24 of the US-Israel military campaign against Iran. Trump issued a 48-hour Hormuz ultimatum on March 21 — deadline is tonight (March 23, 23:44 UTC). Iran has threatened to mine the Strait if the US launches a ground operation. The conflict includes Israeli/US airstrikes on Iran and Iranian missile counterstrikes on Israel (including at Dimona nuclear area, Haifa, Eilat) and US bases.

Generate a situation brief from these {count} intel events from the last {window}:

{events}

Return ONLY valid JSON: {{"en": "<html brief>", "he": "<html brief>"}}"""

def call_llm(events_text, count, window_label, token):
    url = f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/chat/completions?api-version={AOAI_API_VERSION}"
    user_msg = USER_PROMPT_TEMPLATE.format(count=count, window=window_label, events=events_text)
    
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        "max_completion_tokens": 4000,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            # Debug: log raw response
            print(f"[DEBUG {window_label}] Raw LLM response ({len(content)} chars): {content[:300]}...", file=sys.stderr)
            print(f"[DEBUG {window_label}] Full API response keys: {list(data.keys())}", file=sys.stderr)
            choice = data["choices"][0]
            print(f"[DEBUG {window_label}] finish_reason={choice.get('finish_reason')}, content_filter={choice.get('content_filter_results','none')}", file=sys.stderr)
            if not content:
                print(f"[DEBUG {window_label}] EMPTY — full choice: {json.dumps(choice)[:500]}", file=sys.stderr)
            # Try direct JSON parse first
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try extracting from markdown code block
                import re
                # Strip ```json ... ``` wrapper if present
                stripped = re.sub(r'^```(?:json)?\s*', '', content.strip())
                stripped = re.sub(r'\s*```$', '', stripped.strip())
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    pass
                # Try fixing common issues: unescaped newlines in strings
                fixed = stripped.replace('\n', '\\n').replace('\r', '')
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
                # Last resort: extract "en" and "he" values manually
                en_m = re.search(r'"en"\s*:\s*"((?:[^"\\]|\\.)*)"', content, re.DOTALL)
                he_m = re.search(r'"he"\s*:\s*"((?:[^"\\]|\\.)*)"', content, re.DOTALL)
                if en_m or he_m:
                    return {
                        "en": en_m.group(1).replace('\\n', '\n') if en_m else "",
                        "he": he_m.group(1).replace('\\n', '\n') if he_m else ""
                    }
                print(f"Could not parse LLM response: {content[:200]}", file=sys.stderr)
                return None
    except Exception as e:
        if hasattr(e, 'read'):
            body = e.read().decode('utf-8','ignore')[:500]
            print(f"LLM call failed for {window_label}: {e} — {body}", file=sys.stderr)
        else:
            print(f"LLM call failed for {window_label}: {e}", file=sys.stderr)
        return None

def main():
    print(f"[{datetime.now().isoformat()}] Generating briefs...")
    token = _get_token()
    all_events = load_events(max_hours=48)
    print(f"Loaded {len(all_events)} events from last 48h")

    if not all_events:
        print("No events, writing empty brief")
        output = {"generated_at": datetime.now(timezone.utc).isoformat(), "briefs": {}}
        with open(OUTPUT, "w") as f:
            json.dump(output, f, indent=2)
        return

    briefs = {}
    for hours in TIME_WINDOWS:
        filtered = filter_events(all_events, hours)
        if not filtered:
            briefs[str(hours)] = {"en": "<p>No events in this time window.</p>", "he": "<p>אין אירועים בחלון הזמן הזה.</p>", "count": 0}
            continue

        if hours < 1:
            label = f"{int(hours*60)} minutes"
        else:
            label = f"{int(hours)} hours"

        events_text = events_to_text(filtered)
        print(f"  {label}: {len(filtered)} events, {len(events_text)} chars")

        result = call_llm(events_text, len(filtered), label, token)
        if result:
            briefs[str(hours)] = {
                "en": result.get("en", "Brief generation failed."),
                "he": result.get("he", "יצירת התקציר נכשלה."),
                "count": len(filtered),
                "window": label
            }
        else:
            briefs[str(hours)] = {
                "en": f"<p>Brief generation failed for {label} window.</p>",
                "he": f"<p>יצירת תקציר נכשלה עבור חלון של {label}.</p>",
                "count": len(filtered)
            }

        time.sleep(1)  # Rate limit between calls

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "briefs": briefs
    }

    with open(OUTPUT, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Written to {OUTPUT}")

    # Git push
    import subprocess
    try:
        subprocess.run(["git", "add", "docs/brief.json"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"auto: brief {datetime.now().strftime('%H:%M')}"], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True, capture_output=True)
        print("Pushed to GitHub Pages")
    except subprocess.CalledProcessError as e:
        print(f"Git push failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
