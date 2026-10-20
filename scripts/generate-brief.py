#!/usr/bin/env python3
"""
generate-brief.py - Generate LLM-powered intel briefs (EN + HE) from recent events.
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
    # Hardcode dev tenant to avoid breaking when az context switches to corp
    DEV_TENANT_ID = "dc617093-60a7-4d4d-9f6f-828c0db25804"
    try:
        import subprocess
        result = subprocess.run(
            ['az', 'account', 'get-access-token',
             '--resource', 'https://cognitiveservices.azure.com',
             '--tenant', DEV_TENANT_ID,
             '--query', 'accessToken', '-o', 'tsv'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"Auth failed: {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
        return result.stdout.strip()
    except Exception as e:
        print(f"Auth failed: {e}", file=sys.stderr)
        sys.exit(1)

from event_freshness import source_timestamp, fresh_timestamp, relevant_news


def load_events(max_hours=48):
    """Use original publication dates, never the collector's refresh timestamp."""
    events = []
    seen = set()

    def add(item):
        text = (item.get("notes") or item.get("text") or item.get("summary") or "").strip()
        # Exported feed time is HH:MM; its numeric ts is authoritative.
        ts = source_timestamp({"ts": item.get("ts")}) if item.get("ts") else source_timestamp(item)
        if not text or not relevant_news(text) or not fresh_timestamp(ts, max_hours):
            return
        key = text[:200].lower()
        if key in seen:
            return
        seen.add(key)
        events.append({"_ts": ts, "type": "osint", "src": item.get("channel") or item.get("src") or item.get("source", ""),
                       "text": text, "loc": item.get("loc") or item.get("location", ""), "link": item.get("link", "")})

    try:
        with open(INTEL_LOG) as f:
            for line in f:
                try:
                    ev = json.loads(line)
                    if ev.get("alerts"):
                        for alert in ev["alerts"]:
                            # Raw scraped alerts must have an actual source publication date.
                            if fresh_timestamp(source_timestamp(alert), max_hours):
                                add(alert)
                    elif ev.get("type") in ("osint", "breaking_news", "energy_rss"):
                        add(ev)
                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue
    except FileNotFoundError:
        pass
    try:
        with open(INTEL_FEED) as f:
            feed = json.load(f)
        for ev in feed if isinstance(feed, list) else feed.get("events", []):
            # Legacy exports stamped collection time. Reject them until re-exported
            # by the source-time-aware exporter (which supplies observed_at).
            if "observed_at" in ev:
                add(ev)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return sorted(events, key=lambda e: e["_ts"], reverse=True)


def filter_events(events, hours):
    cutoff = time.time() - (hours * 3600)
    return [e for e in events if e.get("_ts", 0) >= cutoff]

def events_to_text(events, max_chars=5000):
    """Convert events to compact text for LLM prompt."""
    lines = []
    for e in events:
        ts = e.get("_ts", 0)
        t = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if ts else "??:??"
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
- GROUND TRUTH — brief ONLY from the events provided in the user message. NEVER introduce outside facts, background history, "Day N of the campaign" counters, ultimatums, pauses, or deadlines that are not present in those events. Inventing continuity or reciting stale history is the single worst failure mode — a sparse brief is always better than a fabricated one.
- Be DIRECT and CONCISE. No fluff. No filler. No "it's important to note".
- Lead with what matters: attacks, military movements, political developments.
- Cut the noise: skip duplicate reports, minor social media chatter, unverified rumors.
- Group related events into themes (e.g. "Northern Border", "Hormuz", "Diplomacy").
- Add tactical context ONLY if explicitly supported by these events. Never infer historical counts.
- Use bullet points. Short sentences. Every word earns its place.
- If there are active sirens or strikes - that goes FIRST, bold.

INTERNATIONAL & GOOD NEWS:
- Include interesting international reactions ONLY if they involve real action (troops moved, sanctions imposed, embargoes, ports closed, emergency sessions). Skip generic "country X condemns" statements.
- European/global news only if genuinely surprising or impactful (e.g. Germany deploys Patriot, Turkey closes strait, oil price shock).
- Do NOT include every politician's opinion or statement. Nobody cares that "French FM expressed concern".
- Actively look for GOOD NEWS: successful interceptions, humanitarian aid arriving, ceasefire talks progressing, civilians rescued, international support with teeth. People need hope too.
- End with a "🟢 Good News" bullet if anything positive happened (even small wins).

BOTTOM LINE:
- Give a threat trend ONLY if supported by these events; otherwise say "Insufficient evidence to assess the trend." Absence of reports is not an all-clear.

FORMAT:
Return a JSON object with two keys:
- "en": English brief (HTML, use <b>, <ul>, <li>, <h3> tags)
- "he": Hebrew brief (HTML, RTL, same content translated naturally - not robotic translation, write like a Hebrew news anchor)

Keep each brief under 300 words. Quality over quantity."""

USER_PROMPT_TEMPLATE = """Today is {today}. You are briefing on the ongoing Iran-Israel-US conflict.

Base the brief ENTIRELY on the {count} intel events below from the last {window}. Do not add context, history, or developments that are not in these events. If the events are sparse, keep the brief short — do not pad it with background.

Intel events (most recent first):

{events}

Return ONLY valid JSON: {{"en": "<html brief>", "he": "<html brief>"}}"""

def call_llm(events_text, count, window_label, token):
    url = f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/chat/completions?api-version={AOAI_API_VERSION}"
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    user_msg = USER_PROMPT_TEMPLATE.format(today=today, count=count, window=window_label, events=events_text)

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
                print(f"[DEBUG {window_label}] EMPTY - full choice: {json.dumps(choice)[:500]}", file=sys.stderr)
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
            print(f"LLM call failed for {window_label}: {e} - {body}", file=sys.stderr)
        else:
            print(f"LLM call failed for {window_label}: {e}", file=sys.stderr)
        return None

def main():
    print(f"[{datetime.now().isoformat()}] Generating briefs...")
    all_events = load_events(max_hours=48)
    print(f"Loaded {len(all_events)} events from last 48h")

    if not all_events:
        print("No events, writing empty brief")
        output = {"generated_at": datetime.now(timezone.utc).isoformat(), "briefs": {}}
        with open(OUTPUT, "w") as f:
            json.dump(output, f, indent=2)
        from publish_generated import publish
        publish(ROOT, ["docs/brief.json"], "brief: no recent source-dated events")
        return

    token = _get_token()
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

    TMP_OUTPUT = os.path.join(ROOT, "state", "brief-pending.json")
    with open(TMP_OUTPUT, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Copy to docs/ (may fail under cron sandbox — use shutil)
    import shutil
    try:
        shutil.copy2(TMP_OUTPUT, OUTPUT)
        print(f"Written to {OUTPUT}")
    except PermissionError:
        # Fallback: use subprocess cp which may have different permissions
        import subprocess
        subprocess.run(["cp", TMP_OUTPUT, OUTPUT], check=True)
        print(f"Written to {OUTPUT} (via cp)")
    
    from publish_generated import publish
    publish(ROOT, ['docs/brief.json'], 'brief: update source-grounded summaries')

if __name__ == "__main__":
    main()
