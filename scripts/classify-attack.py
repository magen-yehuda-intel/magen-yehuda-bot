#!/usr/bin/env python3
"""Classify attack source and weapon type from OSINT + Oref data using Azure OpenAI.

Called by watcher when Oref sirens fire. Reads last 15min of OSINT,
sends to gpt-5-mini for fast classification, outputs JSON.

Usage: python3 classify-attack.py [--oref-areas "area1,area2,..."]
Output: JSON to stdout: {"source","weapon","confidence","reasoning","flight_time_s"}
"""

import json, sys, os, time, urllib.request, urllib.error

AOAI_ENDPOINT = os.environ.get("AOAI_ENDPOINT", "https://openai-dev-nt6mukageprxm.openai.azure.com")
AOAI_DEPLOYMENT = os.environ.get("AOAI_DEPLOYMENT", "gpt-5-mini")
AOAI_API_VERSION = "2025-01-01-preview"

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state")
JSONL_PATH = os.path.join(STATE_DIR, "intel-log.jsonl")

FALLBACK = {"source": "unknown", "weapon": "unknown", "confidence": 0, "reasoning": ""}


def _get_token():
    """Get Azure AD token for Cognitive Services."""
    try:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    except Exception as ex:
        # Fallback: try az cli directly
        import subprocess
        try:
            result = subprocess.run(
                ["az", "account", "get-access-token", "--resource", "https://cognitiveservices.azure.com", "--query", "accessToken", "-o", "tsv"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        return None


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
                    ts = e.get("ts") or e.get("timestamp") or e.get("logged_at", 0)
                    if isinstance(ts, str):
                        continue
                    if ts > cutoff:
                        # Extract individual alerts from batch OSINT entries
                        if "alerts" in e and isinstance(e["alerts"], list):
                            for a in e["alerts"]:
                                events.append(a)
                        else:
                            events.append(e)
                except:
                    continue
    except FileNotFoundError:
        pass
    return events[-50:]  # Last 50 events max


def classify(oref_areas="", osint_events=None):
    token = _get_token()
    if not token:
        return {**FALLBACK, "reasoning": "no Azure AD token"}

    osint_events = osint_events or get_recent_osint()

    # Build OSINT context
    osint_lines = []
    for e in osint_events:
        src = e.get("source", e.get("channel", e.get("src", "?")))
        text = e.get("text", e.get("title", ""))[:200]
        if text:
            osint_lines.append(f"[{src}] {text}")

    osint_context = "\n".join(osint_lines[-30:]) or "(no recent OSINT)"

    system_prompt = (
        "You are a military intelligence analyst. When sirens sound in Israel, "
        "classify the attack based on OSINT intelligence and siren locations.\n\n"
        "Rules:\n"
        "- Northern Israel sirens (Kiryat Shmona, Safed, Nahariya, Haifa, Golan) + Lebanon context = Hezbollah rockets from Lebanon\n"
        "- Southern Israel sirens (Sderot, Ashkelon, Beer Sheva) + Gaza context = Hamas rockets from Gaza\n"
        "- Multiple regions + Iran/IRGC context = Iranian ballistic missiles\n"
        "- UAV/drone/Shahed keywords = uav_drone\n"
        "- Cruise missile keywords = cruise_missile\n"
        "- If unsure set confidence below 0.5\n\n"
        "Respond with ONLY a JSON object with these exact fields:\n"
        "source (iran/yemen/lebanon/iraq/syria/gaza/unknown), "
        "weapon (ballistic_missile/cruise_missile/rocket/uav_drone/mortar/unknown), "
        "sub_type (specific weapon name if identifiable), "
        "confidence (0.0 to 1.0), "
        "reasoning (one sentence), "
        "flight_time_s (estimated seconds from launch to impact, 0 if unknown), "
        "direction (north/south/center/east/multi/unknown)"
    )

    user_msg = f"ACTIVE SIREN AREAS: {oref_areas or 'unknown'}\n\nRECENT OSINT (last 15 minutes):\n{osint_context}"

    url = f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/chat/completions?api-version={AOAI_API_VERSION}"

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        "max_completion_tokens": 4000,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = (result.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            if not text:
                return {**FALLBACK, "reasoning": "empty model response"}
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return json.loads(text)
    except Exception as ex:
        return {**FALLBACK, "reasoning": f"error: {ex}"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--oref-areas", default="", help="Comma-separated Oref alert areas")
    args = parser.parse_args()

    result = classify(oref_areas=args.oref_areas)
    print(json.dumps(result))
