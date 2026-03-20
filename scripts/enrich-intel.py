#!/usr/bin/env python3
"""Batch-enrich OSINT events with LLM-extracted structured intel.

Runs hourly via cron. Pulls unenriched events from Azure Table Storage,
filters for events worth enriching, batches them to gpt-5-mini, and
upserts corrected/enriched fields back to the table.

Usage: python3 enrich-intel.py [--hours 6] [--dry-run] [--limit 100]
"""

import json, sys, os, time, urllib.request, urllib.error, argparse, hashlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import db

AOAI_ENDPOINT = os.environ.get("AOAI_ENDPOINT", "https://openai-dev-nt6mukageprxm.openai.azure.com")
AOAI_DEPLOYMENT = os.environ.get("AOAI_DEPLOYMENT", "gpt-5-mini")
AOAI_API_VERSION = "2025-01-01-preview"

BATCH_SIZE = 10  # events per LLM call
MAX_BATCHES = 10  # cap per run (100 events max)

STATE_DIR = os.path.join(SCRIPT_DIR, "..", "state")
JSONL_PATH = os.path.join(STATE_DIR, "intel-log.jsonl")
ENRICHED_IDS_PATH = os.path.join(STATE_DIR, "enriched-ids.json")

# Country-level centroid coords — events with these are candidates for enrichment
COUNTRY_CENTROIDS = {
    (32.43, 53.69),  # Iran
    (31.77, 35.23),  # Israel
    (32.0, 50.0),    # default/unknown
    (33.85, 35.86),  # Lebanon
    (15.55, 48.52),  # Yemen
    (33.22, 43.68),  # Iraq
    (34.80, 38.99),  # Syria
    (24.71, 46.68),  # Saudi Arabia
}

# Keywords that indicate an event is worth enriching (military/conflict relevance)
WORTH_KEYWORDS = [
    "strike", "struck", "attack", "missile", "drone", "bomb", "eliminat",
    "intercept", "launch", "barrage", "killed", "assassination", "target",
    "explosion", "blast", "shell", "raid", "combat", "shoot", "fire",
    "operation", "offensive", "defend", "naval", "port", "oil", "refinery",
    "nuclear", "base", "airfield", "convoy", "troops", "forces",
    "IRGC", "IDF", "Hezbollah", "Hamas", "Houthi", "CENTCOM", "Basij",
    "casualties", "wounded", "siren", "alarm", "rocket", "debris",
    "infrastructure", "facility", "depot", "command center",
    "tanker", "ship", "vessel", "pipeline", "lng", "natural gas",
    "strait", "hormuz", "suez", "bab el-mandeb", "blockade",
    "sanctions", "embargo", "breaking",
]

# Skip these — not worth LLM tokens
SKIP_KEYWORDS = [
    "pray for", "god bless", "please share", "donate", "subscribe",
    "sponsored content", "breaking: follow", "pizza", "domino",
    "papa john", "freddies beach",
]


def load_enriched_ids():
    """Load set of already-enriched event IDs from local state."""
    try:
        with open(ENRICHED_IDS_PATH) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_enriched_ids(ids):
    """Persist enriched event IDs."""
    # Keep last 5000 to prevent unbounded growth
    trimmed = sorted(ids)[-5000:]
    with open(ENRICHED_IDS_PATH, "w") as f:
        json.dump(trimmed, f)


def load_from_jsonl(hours):
    """Load recent events from local intel-log.jsonl."""
    cutoff = time.time() - (hours * 3600)
    events = []
    enriched_ids = load_enriched_ids()
    try:
        with open(JSONL_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    ts = e.get("ts") or e.get("timestamp") or e.get("logged_at", 0)
                    if isinstance(ts, str):
                        continue
                    if ts < cutoff:
                        continue
                    # Flatten batch OSINT entries with alerts array
                    if e.get("type") == "osint" and "alerts" in e and isinstance(e["alerts"], list):
                        for alert in e["alerts"]:
                            ts_a = alert.get("ts") or alert.get("timestamp") or ts
                            eid = hashlib.md5(f"{alert.get('source','')}{alert.get('text','')}{ts_a}".encode()).hexdigest()[:16]
                            pk = time.strftime("%Y-%m-%d", time.gmtime(ts_a if isinstance(ts_a, (int,float)) else ts))
                            item = {
                                "PartitionKey": pk,
                                "RowKey": eid,
                                "ts": ts_a if isinstance(ts_a, (int,float)) else ts,
                                "src": alert.get("source", alert.get("channel", "")),
                                "text": alert.get("text", ""),
                                "location": alert.get("location", ""),
                                "lat": alert.get("lat", 0),
                                "lon": alert.get("lon", 0),
                                "side": alert.get("side", "unknown"),
                                "link": alert.get("link", ""),
                            }
                            if f"{pk}_{eid}" in enriched_ids:
                                item["enriched"] = True
                            events.append(item)
                        continue

                    # Skip non-text events (blackout, threat_change, etc.)
                    if not e.get("text"):
                        continue

                    # Regular single events
                    eid = hashlib.md5(f"{e.get('src','')}{e.get('text','')}{ts}".encode()).hexdigest()[:16]
                    pk = time.strftime("%Y-%m-%d", time.gmtime(ts))
                    if f"{pk}_{eid}" in enriched_ids:
                        e["enriched"] = True
                    e.setdefault("PartitionKey", pk)
                    e.setdefault("RowKey", eid)
                    e.setdefault("location", e.get("loc", ""))
                    e.setdefault("lat", e.get("lat", 0))
                    e.setdefault("lon", e.get("lon", 0))
                    e.setdefault("side", "unknown")
                    events.append(e)
                except (json.JSONDecodeError, KeyError):
                    continue
    except FileNotFoundError:
        pass
    return events[-500:]


SYSTEM_PROMPT = (
    "You are an OSINT intelligence analyst enriching conflict event data.\n\n"
    "For each event, extract structured fields. Focus on WHAT ACTUALLY HAPPENED and WHERE.\n\n"
    "CRITICAL RULES:\n"
    "- Location = where the event PHYSICALLY occurred, NOT countries merely mentioned\n"
    "- If text says 'Iran attacked Saudi port Yanbu' -> location is Yanbu, Saudi Arabia (NOT Iran)\n"
    "- If text says 'Launches from Iran to Israel' -> location is the LAUNCH site (Iran) unless interception location is specified\n"
    "- attacker = who initiated the action\n"
    "- target_country = country being attacked/affected\n"
    "- If the event is NOT a military/conflict event (opinion, prayer, analysis), set event_category to 'commentary' or 'analysis'\n\n"
    "RANKING FIELDS:\n"
    "- is_breaking: true if this is genuinely breaking news (first report of a new event, not commentary on old events)\n"
    "- market_impact: rate 0-10 how much this could move markets. Guide:\n"
    "  10: Strait of Hormuz blocked, major oil facility destroyed, nuclear strike\n"
    "  8-9: Major oil/LNG infrastructure hit, Suez/Bab el-Mandeb disrupted, sovereign default\n"
    "  6-7: Oil tanker attacked, Saudi/UAE port struck, major pipeline damage, energy embargo\n"
    "  4-5: Military base struck, regional escalation, sanctions announced, refinery fire\n"
    "  2-3: Drone interception, political statement, troop movement, minor skirmish\n"
    "  0-1: Commentary, prayer, analysis, old news rehashed\n"
    "- market_sectors: list of affected sectors e.g. ['oil','natural_gas','defense','shipping','crypto','equities']\n\n"
    "Return a JSON array with one object per event, using the event id field.\n\n"
    "Schema per event:\n"
    '{"id":"event_id","location":"City, Country","lat":float,"lon":float,'
    '"attacker":"iran|israel|us|iran_proxy|russia|unknown",'
    '"target_country":"country name or null",'
    '"target_type":"military_base|oil_infrastructure|gas_infrastructure|civilian|nuclear|air_defense|'
    'command_center|port|airport|government|naval|ship|missile_launcher|pipeline|refinery|lng_terminal|unknown|null",'
    '"attack_type":"missile_strike|drone_strike|airstrike|ground_op|cyber|assassination|naval|interception|launch|null",'
    '"weapon":"ballistic_missile|cruise_missile|drone|aircraft|special_forces|rocket|glide_bomb|torpedo|naval_mine|unknown|null",'
    '"event_category":"strike|interception|political|humanitarian|diplomatic|intelligence|economic|commentary|analysis|breaking",'
    '"severity":"critical|high|medium|low",'
    '"is_breaking":bool,'
    '"market_impact":0-10,'
    '"market_sectors":["oil","natural_gas","defense","shipping","crypto","equities","bonds","insurance"],'
    '"summary":"One clean sentence summarizing the event"}\n\n'
    "Known coordinates:\n"
    "Tehran(35.69,51.39) Isfahan(32.65,51.68) Shiraz(29.59,52.58) Mashhad(36.31,59.6) Bushehr(28.97,50.84) "
    "Natanz(33.51,51.92) Fordow(34.88,51.58) Parchin(35.52,51.77) Arak(34.09,49.69) Tabriz(38.08,46.29) "
    "Ahvaz(31.32,48.67) Dezful(32.38,48.40) Kharg Island(29.24,50.31) Bandar Abbas(27.19,56.27) "
    "Tel Aviv(32.07,34.77) Haifa(32.79,34.99) Jerusalem(31.77,35.23) Gaza(31.5,34.47) "
    "Beirut(33.89,35.5) Damascus(33.51,36.29) Erbil(36.19,44.01) Baghdad(33.31,44.37) "
    "Sanaa(15.37,44.19) Yanbu(24.09,38.06) Ras Tanura(26.64,50.05) Dhahran(26.27,50.21) "
    "Jubail(27.01,49.66) Jeddah(21.49,39.19) Riyadh(24.71,46.68) Abqaiq(25.94,49.68) "
    "Fujairah(25.13,56.33) Doha(25.29,51.53) Strait of Hormuz(26.6,56.3) "
    "Ras Laffan LNG(25.91,51.53) Kharg Island(29.24,50.31) Bab el-Mandeb(12.6,43.3)\n\n"
    'Return ONLY a JSON object with key "events" containing the array: {"events": [...]}'
)


def _get_token():
    """Get Azure AD token for Cognitive Services."""
    try:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    except Exception:
        import subprocess
        try:
            result = subprocess.run(
                ["az", "account", "get-access-token", "--resource",
                 "https://cognitiveservices.azure.com", "--query", "accessToken", "-o", "tsv"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return None


def is_worth_enriching(event):
    """Pre-filter: skip noise, only enrich conflict-relevant events."""
    text = (event.get("text") or "").lower()

    # Skip obvious noise
    if len(text) < 30:
        return False
    for skip in SKIP_KEYWORDS:
        if skip in text:
            return False

    # Must contain at least one conflict-relevant keyword
    for kw in WORTH_KEYWORDS:
        if kw.lower() in text:
            return True

    return False


def needs_enrichment(event):
    """Check if event has not been enriched yet and is worth it."""
    # Already enriched
    if event.get("enriched"):
        return False

    # Check if worth processing
    if not is_worth_enriching(event):
        return False

    return True


def call_llm(events, token):
    """Send batch of events to gpt-5-mini, return enrichment results."""
    # Build event list for prompt
    event_items = []
    for e in events:
        event_items.append({
            "id": f"{e['PartitionKey']}_{e['RowKey']}",
            "src": e.get("src", ""),
            "text": (e.get("text") or "")[:500],
            "current_location": e.get("location", ""),
            "current_lat": e.get("lat", 0),
            "current_lon": e.get("lon", 0),
        })

    user_prompt = f"Enrich these {len(event_items)} OSINT events:\n\n{json.dumps(event_items, indent=1)}"

    url = f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/chat/completions?api-version={AOAI_API_VERSION}"
    body = json.dumps({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "max_completion_tokens": 8000,
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            data = json.loads(raw)
            finish = data["choices"][0].get("finish_reason", "unknown")
            if finish != "stop":
                print(f"[enrich] WARNING: finish_reason={finish} (response may be truncated)")
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            # Handle both {"events": [...]} and direct [...]
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "events" in parsed:
                return parsed["events"]
            # Try to find any list in the response
            for v in parsed.values():
                if isinstance(v, list):
                    return v
            print(f"[enrich] LLM returned unexpected structure: {str(parsed)[:300]}")
            return []
    except json.JSONDecodeError as je:
        print(f"[enrich] LLM returned invalid JSON: {je}")
        print(f"[enrich] Raw content: {content[:500] if 'content' in dir() else 'N/A'}")
        return []
    except Exception as e:
        print(f"[enrich] LLM call failed: {e}")
        if hasattr(e, 'read'):
            try:
                print(f"[enrich] Response body: {e.read().decode()[:500]}")
            except Exception:
                pass
        return []


def apply_enrichment(event, enrichment, dry_run=False):
    """Upsert enriched fields back to table."""
    pk = event["PartitionKey"]
    rk = event["RowKey"]

    update = {
        "PartitionKey": pk,
        "RowKey": rk,
    }

    # Copy existing fields
    for k in ["ts", "src", "text", "side", "type", "sub_event_type", "breaking",
              "confidence", "link", "raw_json"]:
        if k in event:
            update[k] = event[k]

    # Apply enriched fields
    if enrichment.get("lat") and enrichment.get("lon"):
        update["lat"] = float(enrichment["lat"])
        update["lon"] = float(enrichment["lon"])
    if enrichment.get("location"):
        update["location"] = enrichment["location"]

    # Map attacker to side if we got a better signal
    if enrichment.get("attacker") and enrichment["attacker"] != "unknown":
        update["side"] = enrichment["attacker"]

    # New enriched fields
    for field in ["attacker", "target_country", "target_type", "attack_type",
                  "weapon", "event_category", "severity", "summary",
                  "is_breaking", "market_impact"]:
        if enrichment.get(field) is not None:
            update[field] = enrichment[field] if isinstance(enrichment[field], (bool, int, float)) else str(enrichment[field])

    # Store market_sectors as comma-separated string (Table Storage doesn't support arrays)
    if enrichment.get("market_sectors"):
        update["market_sectors"] = ",".join(enrichment["market_sectors"]) if isinstance(enrichment["market_sectors"], list) else str(enrichment["market_sectors"])

    update["enriched"] = True
    update["enriched_at"] = time.time()

    if dry_run:
        loc = enrichment.get("location", "?")
        summary = enrichment.get("summary", "")[:80]
        print(f"  [DRY] {pk}/{rk[:8]}.. -> {loc} | {summary}")
        return True

    # Write to DB if available
    try:
        client = db._get_client()
        client.upsert_entity(update)
    except Exception as e:
        print(f"[enrich] DB upsert skipped ({e.__class__.__name__}), saving locally")

    # Always write enriched event to local JSONL
    enriched_path = os.path.join(STATE_DIR, "enriched-intel.jsonl")
    with open(enriched_path, "a") as f:
        f.write(json.dumps(update, default=str) + "\n")

    # Track enriched IDs locally
    enriched_ids = load_enriched_ids()
    enriched_ids.add(f"{pk}_{rk}")
    save_enriched_ids(enriched_ids)

    return True


def main():
    parser = argparse.ArgumentParser(description="Batch-enrich OSINT events with LLM")
    parser.add_argument("--hours", type=int, default=6, help="Look back N hours (default 6)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--limit", type=int, default=100, help="Max events to process")
    args = parser.parse_args()

    print(f"[enrich] Starting — lookback {args.hours}h, limit {args.limit}, dry_run={args.dry_run}")

    # Fetch recent events — try DB first, fall back to local JSONL
    events = []
    source = "unknown"
    try:
        events = db.query_events(hours=args.hours, limit=500)
        if events:
            source = "db"
            print(f"[enrich] Fetched {len(events)} events from DB (last {args.hours}h)")
        else:
            raise ValueError("DB returned 0 events, trying JSONL")
    except Exception as e:
        print(f"[enrich] DB unavailable or empty, falling back to local JSONL")
        events = load_from_jsonl(args.hours)
        source = "jsonl"
        print(f"[enrich] Loaded {len(events)} events from JSONL (last {args.hours}h)")

    # Filter to those needing enrichment
    candidates = [e for e in events if needs_enrichment(e)]
    candidates = candidates[:args.limit]
    print(f"[enrich] {len(candidates)} candidates after filtering")

    if not candidates:
        print("[enrich] Nothing to enrich")
        return

    # Get token
    token = _get_token()
    if not token:
        print("[enrich] ERROR: No Azure AD token available")
        return

    # Process in batches
    total_ok, total_fail, total_skip = 0, 0, 0
    for batch_idx in range(0, min(len(candidates), MAX_BATCHES * BATCH_SIZE), BATCH_SIZE):
        batch = candidates[batch_idx:batch_idx + BATCH_SIZE]
        if not batch:
            break

        print(f"[enrich] Batch {batch_idx // BATCH_SIZE + 1}: {len(batch)} events")
        results = call_llm(batch, token)

        if not results:
            print(f"[enrich] Batch returned no results")
            total_fail += len(batch)
            continue

        # Build lookup by id
        result_map = {}
        for r in results:
            if not isinstance(r, dict):
                continue
            rid = r.get("id", "")
            result_map[rid] = r

        # Apply results
        for event in batch:
            eid = f"{event['PartitionKey']}_{event['RowKey']}"
            enrichment = result_map.get(eid)
            if not enrichment:
                total_skip += 1
                continue

            if apply_enrichment(event, enrichment, dry_run=args.dry_run):
                total_ok += 1
            else:
                total_fail += 1

        # Rate limit between batches
        if batch_idx + BATCH_SIZE < len(candidates):
            time.sleep(2)

    print(f"[enrich] Done — enriched={total_ok}, failed={total_fail}, skipped={total_skip}")


if __name__ == "__main__":
    main()
