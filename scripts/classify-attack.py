#!/usr/bin/env python3
"""Classify attack source and weapon type from OSINT + Oref data using Gemini Flash.

Called by watcher when Oref sirens fire. Reads last 15min of OSINT,
sends to Gemini 2.0 Flash for fast classification, outputs JSON.

Usage: python3 classify-attack.py [--oref-areas "area1,area2,..."]
Output: JSON to stdout: {"source","weapon","confidence","reasoning","flight_time_s"}
"""

import json, sys, os, time, urllib.request, urllib.error

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODELS = ["gemini-2.0-flash-lite", "gemini-2.0-flash"]

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state")
JSONL_PATH = os.path.join(STATE_DIR, "intel-log.jsonl")

def get_recent_osint(minutes=15):
    """Read last N minutes of OSINT from intel-log.jsonl."""
    cutoff = time.time() - (minutes * 60)
    events = []
    try:
        with open(JSONL_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    ts = e.get("ts") or e.get("timestamp", 0)
                    if isinstance(ts, str):
                        continue
                    if ts > cutoff:
                        events.append(e)
                except:
                    continue
    except FileNotFoundError:
        pass
    return events[-50:]  # Last 50 events max

def classify(oref_areas="", osint_events=None):
    if not GEMINI_API_KEY:
        return {"source": "unknown", "weapon": "unknown", "confidence": 0, "reasoning": "no API key"}

    osint_events = osint_events or get_recent_osint()
    
    # Build OSINT context
    osint_lines = []
    for e in osint_events:
        src = e.get("src", e.get("source", "?"))
        text = e.get("text", e.get("title", ""))[:200]
        if text:
            osint_lines.append(f"[{src}] {text}")
    
    osint_context = "\n".join(osint_lines[-30:]) or "(no recent OSINT)"

    prompt = f"""You are a military intelligence analyst. Sirens are active in Israel.
Based on the OSINT intelligence below, classify the attack.

ACTIVE SIREN AREAS: {oref_areas or 'unknown'}

RECENT OSINT (last 15 minutes):
{osint_context}

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "source": "iran|yemen|lebanon|iraq|syria|gaza|unknown",
  "weapon": "ballistic_missile|cruise_missile|rocket|uav_drone|mortar|unknown",
  "sub_type": "specific weapon name if identifiable, e.g. Shahab-3, Shahed-136, Grad, Fateh-110",
  "confidence": 0.0-1.0,
  "reasoning": "one sentence explaining why",
  "flight_time_s": estimated seconds from launch to impact (0 if unknown),
  "direction": "north|south|center|east|multi|unknown"
}}

Key rules:
- "שיגור מלבנון" = launch from Lebanon = source:lebanon, weapon:rocket
- Northern Israel sirens (Kiryat Shmona, Safed, Haifa, Golan) + Lebanon context = Hezbollah rockets
- Southern Israel sirens (Sderot, Ashkelon, Beer Sheva) + Gaza context = Hamas rockets
- Multiple regions + Iran/IRGC context = Iranian ballistic missiles
- "כטבמ"/"מזל״ט"/"drone"/"Shahed" = UAV
- "טיל שיוט"/"cruise" = cruise missile
- If unsure, say confidence < 0.5"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 300,
            "responseMimeType": "application/json",
        }
    }

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
        except urllib.error.HTTPError as he:
            if he.code == 429:
                continue  # Try next model
            return {"source": "unknown", "weapon": "unknown", "confidence": 0, "reasoning": f"error: {he}"}
        except Exception as ex:
            return {"source": "unknown", "weapon": "unknown", "confidence": 0, "reasoning": f"error: {ex}"}
    return {"source": "unknown", "weapon": "unknown", "confidence": 0, "reasoning": "all models rate-limited"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--oref-areas", default="", help="Comma-separated Oref alert areas")
    args = parser.parse_args()
    
    result = classify(oref_areas=args.oref_areas)
    print(json.dumps(result))
