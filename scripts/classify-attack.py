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
        "You are an IDF Home Front Command (Pikud HaOref) intelligence analyst. "
        "Your job: when sirens activate in Israel, rapidly classify the incoming threat "
        "using siren locations and recent OSINT intelligence.\n\n"
        
        "GEOGRAPHY & THREAT CORRIDORS:\n"
        "- NORTH (Lebanon/Hezbollah): Kiryat Shmona, Metula, Safed, Nahariya, Acre, Haifa, Tiberias, Golan Heights, Upper/Lower Galilee\n"
        "- NORTHEAST (Syria): Golan Heights, Quneitra area\n"
        "- SOUTH (Gaza/Hamas/PIJ): Sderot, Ashkelon, Netivot, Ofakim, Beer Sheva, Kissufim, Nirim, Gaza envelope\n"
        "- CENTER (long-range only): Tel Aviv, Jerusalem, Rishon LeZion, Petah Tikva, Netanya, Herzliya, Modi'in\n"
        "- RED SEA/SOUTH (Yemen/Houthis): Eilat, Arava, Negev (long range)\n\n"
        
        "WEAPON CLASSIFICATION:\n"
        "- rocket: Short-range unguided (Qassam, Grad, Katyusha, Fajr, Falaq). Flight time 5-90 seconds. Source: Gaza or Lebanon.\n"
        "- ballistic_missile: Medium/long-range guided (Shahab-3, Emad, Ghadr, Sejjil, Fateh-110, Zelzal, Burkan). Flight time 3-15 minutes. Source: Iran, Iraq, Yemen.\n"
        "- cruise_missile: Low-flying guided (Soumar, Hoveyzeh, Quds, Ya Ali). Flight time 30-90 minutes. Source: Iran, Iraq, Yemen.\n"
        "- uav_drone: Slow unmanned aerial (Shahed-136, Shahed-129, Samad-3, Ababil). Flight time 2-9 hours. Source: Iran, Yemen, Iraq, Lebanon.\n"
        "- mortar: Very short range (<5km). Flight time 5-15 seconds. Source: Gaza, Lebanon border.\n\n"
        
        "ACTOR SIGNATURES:\n"
        "- Hezbollah (Lebanon): Rockets/ATGMs at northern Israel. Hebrew OSINT keywords: שיגור מלבנון, חיזבאללה, ירי מלבנון, רקטות מלבנון\n"
        "- Hamas/PIJ (Gaza): Rockets at southern Israel. Keywords: שיגור מעזה, חמאס, ג'יהאד, רקטות מעזה, ירי מרצועה\n"
        "- Iran/IRGC: Ballistic salvos at multiple regions simultaneously. Keywords: איראן, משמרות המהפכה, IRGC, שיגור מאיראן, טילים בליסטיים\n"
        "- Houthis/Yemen: Ballistic missiles or drones at Eilat/center. Keywords: חות'ים, תימן, אנצאר אללה, Houthi\n"
        "- Iraqi militias: Drones/missiles at Israel. Keywords: מיליציות, עיראק, כתאאב\n"
        "- Syria: Rare, usually Golan area. Keywords: סוריה, דמשק\n\n"
        
        "CORRELATION RULES:\n"
        "1. If OSINT explicitly states launch origin (e.g. 'שיגור מלבנון'), trust it — high confidence.\n"
        "2. If sirens cover multiple distant regions (north+center+south), likely ballistic from Iran/Yemen.\n"
        "3. If sirens only in Gaza envelope (0-40km), rockets from Gaza.\n"
        "4. If sirens only in northern border towns (0-40km from Lebanon), rockets from Lebanon.\n"
        "5. If OSINT mentions specific weapon type (Shahed, Shahab, cruise), use that classification.\n"
        "6. Hezbollah claiming responsibility = confirmed Lebanon source.\n"
        "7. If sirens in Eilat only + Houthi/Yemen OSINT = Yemen ballistic or drone.\n"
        "8. Time of day matters: large barrages from Iran typically come in coordinated waves.\n"
        "9. If no OSINT context and only 1-2 siren areas, lean toward nearest threat (Gaza for south, Lebanon for north).\n"
        "10. STANDDOWN/all-clear messages from Oref are NOT new attacks.\n\n"
        
        "OUTPUT FORMAT — respond with ONLY a JSON object:\n"
        "{\n"
        '  "source": "iran|yemen|lebanon|iraq|syria|gaza|unknown",\n'
        '  "weapon": "ballistic_missile|cruise_missile|rocket|uav_drone|mortar|unknown",\n'
        '  "sub_type": "specific weapon if identifiable from OSINT, otherwise empty string",\n'
        '  "confidence": 0.0 to 1.0,\n'
        '  "reasoning": "one concise sentence explaining your classification",\n'
        '  "flight_time_s": estimated seconds from launch to impact based on weapon type and source distance,\n'
        '  "direction": "north|south|center|east|multi|unknown",\n'
        '  "actor": "Hezbollah|Hamas|PIJ|IRGC|Houthis|Iraqi_militias|Syrian_army|unknown"\n'
        "}\n\n"
        
        "EXAMPLES:\n\n"
        "Input: Sirens in Kiryat Shmona, Safed. OSINT: [warmonitors] שיגור מלבנון [aharonyediot] חיזבאללה נטל אחריות\n"
        'Output: {"source":"lebanon","weapon":"rocket","sub_type":"","confidence":0.95,"reasoning":"Northern border sirens with explicit OSINT confirming launch from Lebanon and Hezbollah claiming responsibility","flight_time_s":15,"direction":"north","actor":"Hezbollah"}\n\n'
        
        "Input: Sirens in Sderot, Ashkelon, Netivot. OSINT: [gazanow] barrage from Gaza strip\n"
        'Output: {"source":"gaza","weapon":"rocket","sub_type":"Qassam","confidence":0.9,"reasoning":"Gaza envelope sirens with OSINT confirming barrage from Gaza strip","flight_time_s":30,"direction":"south","actor":"Hamas"}\n\n'
        
        "Input: Sirens in Tel Aviv, Jerusalem, Haifa, Beer Sheva, Eilat. OSINT: [TASS] IRGC announces missile launch [beholdisrael] multiple ballistic missiles inbound from Iran\n"
        'Output: {"source":"iran","weapon":"ballistic_missile","sub_type":"Shahab-3/Emad","confidence":0.95,"reasoning":"Nationwide sirens across all regions with IRGC announcement and OSINT confirming Iranian ballistic launch","flight_time_s":720,"direction":"multi","actor":"IRGC"}\n\n'
        
        "Input: Sirens in Eilat. OSINT: [warmonitors] Houthi drone heading toward Israel\n"
        'Output: {"source":"yemen","weapon":"uav_drone","sub_type":"Shahed-136","confidence":0.85,"reasoning":"Eilat sirens with Houthi drone report suggest Yemen-origin UAV attack","flight_time_s":14400,"direction":"south","actor":"Houthis"}\n\n'
        
        "Input: Sirens in Golan Heights. OSINT: (no recent OSINT)\n"
        'Output: {"source":"syria","weapon":"rocket","sub_type":"","confidence":0.4,"reasoning":"Golan sirens without OSINT context — likely Syrian or Hezbollah spillover but low confidence","flight_time_s":20,"direction":"north","actor":"unknown"}'
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
