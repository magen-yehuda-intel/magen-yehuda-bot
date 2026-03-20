#!/usr/bin/env python3
"""Tests for write-live-event.py — classification → live event pipeline."""

import json, os, sys, tempfile, time, unittest

# Add scripts dir to path
SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPT_DIR)

# Must patch DOCS_DIR before import
import write_live_event  # will fail if file has hyphens

class TestBuildEvent(unittest.TestCase):
    """Test event construction from classification output."""

    def test_iran_ballistic(self):
        c = {"source": "iran", "weapon": "ballistic_missile", "actor": "IRGC",
             "direction": "multi", "confidence": 0.95, "reasoning": "Nationwide sirens",
             "sub_type": "Shahab-3"}
        ev = write_live_event.build_event(c, "Tel Aviv,Jerusalem,Haifa")
        self.assertIsNotNone(ev)
        self.assertEqual(ev["type"], "missile")
        self.assertEqual(ev["origin_lat"], 33.5)
        self.assertEqual(ev["origin_lon"], 48.5)
        self.assertEqual(ev["source_country"], "iran")
        self.assertEqual(ev["severity"], "critical")
        self.assertTrue(ev["live"])
        self.assertIn("Shahab-3", ev["desc"])

    def test_lebanon_rocket(self):
        c = {"source": "lebanon", "weapon": "rocket", "actor": "Hezbollah",
             "direction": "north", "confidence": 0.9, "reasoning": "Northern sirens"}
        ev = write_live_event.build_event(c, "Kiryat Shmona,Safed")
        self.assertIsNotNone(ev)
        self.assertEqual(ev["origin_lat"], 33.85)
        self.assertAlmostEqual(ev["origin_lon"], 35.86)
        self.assertEqual(ev["target"], "Kiryat Shmona")

    def test_gaza_rocket(self):
        c = {"source": "gaza", "weapon": "rocket", "actor": "Hamas",
             "direction": "south", "confidence": 0.85, "reasoning": "Gaza envelope sirens"}
        ev = write_live_event.build_event(c, "Sderot,Ashkelon")
        self.assertIsNotNone(ev)
        self.assertEqual(ev["origin_lat"], 31.42)

    def test_yemen_drone(self):
        c = {"source": "yemen", "weapon": "uav_drone", "actor": "Houthis",
             "direction": "south", "confidence": 0.8, "reasoning": "Eilat sirens + Houthi OSINT"}
        ev = write_live_event.build_event(c, "Eilat")
        self.assertIsNotNone(ev)
        self.assertAlmostEqual(ev["origin_lat"], 15.35)

    def test_unknown_source_returns_none(self):
        c = {"source": "unknown", "weapon": "unknown", "confidence": 0}
        ev = write_live_event.build_event(c)
        self.assertIsNone(ev)

    def test_low_confidence_returns_none(self):
        c = {"source": "iran", "weapon": "ballistic_missile", "confidence": 0.1}
        ev = write_live_event.build_event(c)
        self.assertIsNone(ev)

    def test_high_severity_threshold(self):
        # confidence < 0.7 → "high" not "critical"
        c = {"source": "iran", "weapon": "ballistic_missile", "confidence": 0.5, "direction": "center"}
        ev = write_live_event.build_event(c)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["severity"], "high")

    def test_no_oref_areas_uses_direction_label(self):
        c = {"source": "iran", "weapon": "ballistic_missile", "confidence": 0.9, "direction": "center"}
        ev = write_live_event.build_event(c, "")
        self.assertEqual(ev["target"], "Tel Aviv metro")

    def test_event_has_timestamp(self):
        c = {"source": "iran", "weapon": "ballistic_missile", "confidence": 0.9, "direction": "multi"}
        ev = write_live_event.build_event(c)
        self.assertIn("ts", ev)
        self.assertAlmostEqual(ev["ts"], int(time.time()), delta=5)


class TestWriteEvent(unittest.TestCase):
    """Test file write/dedup logic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_path = write_live_event.LIVE_EVENTS_PATH
        write_live_event.LIVE_EVENTS_PATH = os.path.join(self.tmpdir, "live-events.json")

    def tearDown(self):
        write_live_event.LIVE_EVENTS_PATH = self.orig_path
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_new_event(self):
        ev = {"source_country": "iran", "weapon_type": "ballistic_missile", "ts": int(time.time()),
              "origin_lat": 33.5, "origin_lon": 48.5, "lat": 32.085, "lon": 34.781}
        result = write_live_event.write_event(ev)
        self.assertTrue(result)
        with open(write_live_event.LIVE_EVENTS_PATH) as f:
            data = json.load(f)
        self.assertEqual(len(data["events"]), 1)
        self.assertIn("updated", data)

    def test_dedup_same_source_within_120s(self):
        now = int(time.time())
        ev1 = {"source_country": "iran", "weapon_type": "ballistic_missile", "ts": now,
               "origin_lat": 33.5, "origin_lon": 48.5}
        ev2 = {"source_country": "iran", "weapon_type": "ballistic_missile", "ts": now + 60,
               "origin_lat": 33.5, "origin_lon": 48.5}
        write_live_event.write_event(ev1)
        result = write_live_event.write_event(ev2)
        self.assertFalse(result)  # should be deduped
        with open(write_live_event.LIVE_EVENTS_PATH) as f:
            data = json.load(f)
        self.assertEqual(len(data["events"]), 1)

    def test_different_source_not_deduped(self):
        now = int(time.time())
        ev1 = {"source_country": "iran", "weapon_type": "ballistic_missile", "ts": now,
               "origin_lat": 33.5, "origin_lon": 48.5}
        ev2 = {"source_country": "lebanon", "weapon_type": "rocket", "ts": now + 30,
               "origin_lat": 33.85, "origin_lon": 35.86}
        write_live_event.write_event(ev1)
        result = write_live_event.write_event(ev2)
        self.assertTrue(result)
        with open(write_live_event.LIVE_EVENTS_PATH) as f:
            data = json.load(f)
        self.assertEqual(len(data["events"]), 2)

    def test_max_events_trimmed(self):
        write_live_event.MAX_EVENTS = 5
        for i in range(8):
            ev = {"source_country": f"src_{i}", "weapon_type": "rocket", "ts": int(time.time()) + i * 200,
                  "origin_lat": 33.0, "origin_lon": 48.0}
            write_live_event.write_event(ev)
        with open(write_live_event.LIVE_EVENTS_PATH) as f:
            data = json.load(f)
        self.assertEqual(len(data["events"]), 5)
        write_live_event.MAX_EVENTS = 20  # restore

    def test_corrupted_file_recovery(self):
        with open(write_live_event.LIVE_EVENTS_PATH, "w") as f:
            f.write("NOT JSON{{{")
        ev = {"source_country": "iran", "weapon_type": "ballistic_missile", "ts": int(time.time()),
              "origin_lat": 33.5, "origin_lon": 48.5}
        result = write_live_event.write_event(ev)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
