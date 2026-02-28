#!/usr/bin/env python3
"""
Iran Internet Blackout Detector.
Monitors internet connectivity in Iran via multiple methods:
1. IODA (Internet Outage Detection & Analysis) - Georgia Tech
2. Cloudflare Radar (traffic trends)
3. Direct probe to Iranian endpoints

Outputs JSON with connectivity status and alerts.

Usage:
    python3 scan-blackout.py <config.json> <state_dir> [--seed]
"""

import sys
import os
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta

# Iranian ASNs to monitor (major ISPs)
IRAN_ASNS = {
    "AS12880": "DCI (Data Communication Company of Iran)",
    "AS44244": "Irancell (MTN)",
    "AS197207": "Mobile Communication Company of Iran",
    "AS58224": "TCI (Telecommunication Company of Iran)",
    "AS43754": "Asiatech",
    "AS16322": "Pars Online",
}

# Iranian endpoints to probe (government/news sites)
IRAN_PROBE_URLS = [
    "https://www.irna.ir",          # IRNA state news
    "https://president.ir",         # Presidency
    "https://en.mehrnews.com",      # Mehr News
]


def check_ioda(state_dir):
    """Check IODA for Iran internet outages."""
    try:
        now = int(time.time())
        start = now - 7200  # last 2 hours for better signal
        url = f"https://api.ioda.inetintel.cc.gatech.edu/v2/signals/raw/country/IR?from={start}&until={now}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "MagenYehudaBot/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        # Parse nested structure: data -> [[{signal1}, {signal2}]]
        raw_data = data.get("data", [])
        signals_list = []
        for group in raw_data:
            if isinstance(group, list):
                for sig in group:
                    if isinstance(sig, dict):
                        signals_list.append(sig)
            elif isinstance(group, dict):
                signals_list.append(group)
        
        if not signals_list:
            return {"source": "ioda", "status": "no_data", "detail": "No IODA signals available"}
        
        results = []
        for signal in signals_list:
            source_name = signal.get("datasource", "")
            values = signal.get("values", [])
            if not values:
                continue
            # Skip complex nested value types (gtr-sarima has dicts inside)
            recent = []
            for v in values:
                if isinstance(v, (int, float)):
                    recent.append(v)
            if len(recent) < 2:
                continue
            avg = sum(recent) / len(recent)
            latest = recent[-1]
            if avg > 0:
                ratio = latest / avg
                results.append({
                    "datasource": source_name,
                    "entity": signal.get("entityFqid", ""),
                    "latest": latest,
                    "avg": round(avg, 1),
                    "ratio": round(ratio, 3),
                    "drop_pct": round((1 - ratio) * 100, 1),
                })
        
        return {"source": "ioda", "status": "ok", "signals": results}
    except urllib.error.HTTPError as e:
        return {"source": "ioda", "status": "error", "detail": f"HTTP {e.code}"}
    except Exception as e:
        return {"source": "ioda", "status": "error", "detail": str(e)[:200]}


def check_cloudflare_radar():
    """Check Cloudflare Radar for Iran traffic anomalies via connectivity endpoint."""
    try:
        url = "https://radar.cloudflare.com/api/v1/annotations/outages?dateRange=1d&format=json"
        req = urllib.request.Request(url, headers={
            "User-Agent": "MagenYehudaBot/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        # Look for Iran-related outages
        outages = data.get("result", {}).get("annotations", [])
        iran_outages = []
        for o in outages:
            locations = o.get("locations", "")
            if "IR" in locations or "Iran" in str(o):
                iran_outages.append({
                    "start": o.get("startDate", ""),
                    "end": o.get("endDate", ""),
                    "description": o.get("description", "")[:200],
                })
        
        return {
            "source": "cloudflare",
            "status": "ok",
            "iran_outages": iran_outages,
            "total_global_outages": len(outages),
        }
    except Exception as e:
        return {"source": "cloudflare", "status": "error", "detail": str(e)[:200]}


def probe_iranian_endpoints():
    """Direct probe Iranian government websites."""
    results = []
    for url in IRAN_PROBE_URLS:
        start = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                code = resp.status
                latency = round((time.time() - start) * 1000)
                results.append({"url": url, "status": code, "latency_ms": latency, "reachable": True})
        except urllib.error.HTTPError as e:
            latency = round((time.time() - start) * 1000)
            results.append({"url": url, "status": e.code, "latency_ms": latency, "reachable": True})
        except Exception as e:
            latency = round((time.time() - start) * 1000)
            results.append({"url": url, "status": 0, "latency_ms": latency, "reachable": False, "error": str(e)[:100]})
    
    reachable = sum(1 for r in results if r["reachable"])
    return {
        "source": "direct_probe",
        "status": "ok",
        "reachable": reachable,
        "total": len(results),
        "probes": results,
    }


def assess_blackout(ioda, cloudflare, probes, state_dir):
    """Assess overall internet status and detect blackouts."""
    score = 0  # 0 = normal, higher = more likely blackout
    signals = []
    
    # IODA signals
    ioda_details = []
    if ioda.get("signals"):
        for sig in ioda["signals"]:
            drop = sig.get("drop_pct", 0)
            ds = sig.get("datasource", "?")
            if drop > 50:
                score += 40
                signals.append(f"IODA {ds}: {drop}% drop")
            elif drop > 25:
                score += 20
                signals.append(f"IODA {ds}: {drop}% drop")
            elif drop > 10:
                score += 5
                signals.append(f"IODA {ds}: {drop}% drop")
            ioda_details.append({"source": ds, "drop_pct": round(drop, 1)})
    
    # Probe results
    if probes.get("total", 0) > 0:
        unreachable_pct = ((probes["total"] - probes["reachable"]) / probes["total"]) * 100
        if unreachable_pct >= 100:
            score += 30
            signals.append(f"All {probes['total']} Iranian endpoints unreachable")
        elif unreachable_pct >= 50:
            score += 15
            signals.append(f"{probes['total'] - probes['reachable']}/{probes['total']} Iranian endpoints down")
    
    # Classify
    if score >= 50:
        level = "BLACKOUT"
        emoji = "⚫"
    elif score >= 25:
        level = "DEGRADED"
        emoji = "🟡"
    elif score >= 10:
        level = "MINOR_ISSUES"
        emoji = "🟠"
    else:
        level = "NORMAL"
        emoji = "🟢"
    
    # ── History tracking for graph ──
    state_file = os.path.join(state_dir, "blackout-state.json")
    history_file = os.path.join(state_dir, "blackout-history.json")
    prev_level = "NORMAL"
    prev_alert_ts = 0
    try:
        with open(state_file) as f:
            prev = json.load(f)
            prev_level = prev.get("level", "NORMAL")
            prev_alert_ts = prev.get("last_alert_ts", 0)
    except:
        pass
    
    changed = (level != prev_level)
    now_ts = time.time()
    
    # Load history (keep 24h rolling)
    history = []
    try:
        with open(history_file) as f:
            history = json.load(f)
    except:
        pass
    cutoff = now_ts - 86400
    history = [h for h in history if h.get("ts", 0) > cutoff]
    history.append({"ts": now_ts, "score": score, "level": level})
    with open(history_file, "w") as f:
        json.dump(history, f)
    
    # Save state
    state = {
        "level": level,
        "score": score,
        "ts": now_ts,
        "utc": datetime.now(timezone.utc).isoformat(),
        "last_alert_ts": prev_alert_ts,
    }
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    
    return {
        "level": level,
        "emoji": emoji,
        "score": score,
        "changed": changed,
        "prev_level": prev_level,
        "signals": signals,
        "ioda_details": ioda_details,
        "last_alert_ts": prev_alert_ts,
        "history": history[-24:],  # last 24 data points for graph
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scan-blackout.py <config.json> <state_dir> [--seed]", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    seed_mode = "--seed" in sys.argv
    
    os.makedirs(state_dir, exist_ok=True)
    
    print("  Checking Iran internet status...", file=sys.stderr)
    
    # Run all checks
    ioda = check_ioda(state_dir)
    print(f"  IODA: {ioda.get('status', '?')}", file=sys.stderr)
    
    cloudflare = check_cloudflare_radar()
    print(f"  Cloudflare: {cloudflare.get('status', '?')}", file=sys.stderr)
    
    probes = probe_iranian_endpoints()
    print(f"  Probes: {probes['reachable']}/{probes['total']} reachable", file=sys.stderr)
    
    # Assess
    assessment = assess_blackout(ioda, cloudflare, probes, state_dir)
    print(f"  Assessment: {assessment['emoji']} {assessment['level']} (score: {assessment['score']})", file=sys.stderr)
    
    result = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "assessment": assessment,
        "ioda": ioda,
        "cloudflare": cloudflare,
        "probes": probes,
        "seed_mode": seed_mode,
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
