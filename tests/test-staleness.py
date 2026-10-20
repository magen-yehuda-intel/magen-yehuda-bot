#!/usr/bin/env python3
"""Regression gates for source-dated news, retired deadlines and publication."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from email.utils import formatdate
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from event_freshness import source_timestamp, fresh_timestamp, relevant_news
from publish_generated import publish


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FreshnessTests(unittest.TestCase):
    def test_source_date_wins_over_collector(self):
        now = time.time()
        old = {'time': '2026-04-07T00:00:00Z', 'ts': now}
        self.assertFalse(fresh_timestamp(source_timestamp(old)))
        self.assertIsNone(source_timestamp({'time': 'bad', 'ts': now}))
        self.assertIsNone(source_timestamp({}))

    def test_date_formats_and_invalid(self):
        now = int(time.time()) - 10
        for value in (now, now * 1000, formatdate(now, usegmt=True), datetime.fromtimestamp(now, timezone.utc).isoformat()):
            self.assertTrue(fresh_timestamp(source_timestamp({'time': value})))
        for value in ('garbage', '2026-10-20', float('nan'), True):
            self.assertIsNone(source_timestamp({'time': value}))
        self.assertFalse(fresh_timestamp(time.time() + 3600))

    def test_scope(self):
        self.assertFalse(relevant_news('AfD hit by cyberattack, over 400,000 emails leaked online'))
        self.assertTrue(relevant_news('Iran threatens shipping in the Strait of Hormuz'))
        self.assertTrue(relevant_news('דיווח חדש על איראן'))

    def test_energy_rss_unknown_and_future_not_now(self):
        m = module('scan-energy-rss')
        for date in ('bad', '', formatdate(time.time() + 3600, usegmt=True), 'Tue, 07 Apr 2026 00:00:00 GMT'):
            rss = f'<rss><channel><item><title>Iran oil report</title><pubDate>{date}</pubDate></item></channel></rss>'
            self.assertEqual(m.parse_rss(rss, 'fixture'), [])
        rss = f'<rss><channel><item><title>Iran oil report</title><pubDate>{formatdate(time.time()-30, usegmt=True)}</pubDate></item></channel></rss>'
        self.assertEqual(len(m.parse_rss(rss, 'fixture')), 1)

    def test_brief_flattens_source_dated_alerts(self):
        m = module('generate-brief')
        now = time.time()
        fresh = {'text': 'Iran reports fresh development in diplomatic negotiations', 'time': formatdate(now-20, usegmt=True), 'channel': 'fixture'}
        stale = {'text': 'Iran Trump energy pause expired April 6', 'time': '2026-04-07T00:00:00Z'}
        unknown = {'text': 'Iran report without publication date'}
        noise = {'text': 'AfD cyberattack reported', 'time': fresh['time']}
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
            log = Path(td)/'log.jsonl'; feed = Path(td)/'feed.json'
            log.write_text(json.dumps({'logged_at': now, 'type': 'osint', 'alerts': [fresh, stale, unknown, noise]})+'\n')
            feed.write_text(json.dumps({'events': [{'ts': now, 'text': 'Iran old export timestamp'}]}))
            with patch.object(m, 'INTEL_LOG', str(log)), patch.object(m, 'INTEL_FEED', str(feed)):
                rows = m.load_events()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['text'], fresh['text'])
            self.assertIn('UTC', m.events_to_text(rows))

    def test_export_preserves_publication_dates_and_pushes_newest_slice(self):
        m = module('export-feed')
        now = int(time.time())
        alerts = [{'text': f'Iran source report number {i:03d} with regional updates',
                   'time': formatdate(now - 30 - i * 60, usegmt=True), 'channel': 'fixture'}
                  for i in range(105)]
        alerts += [{'text': 'Iran stale report collected today', 'time': '2026-04-07T00:00:00Z'},
                   {'text': 'Iran unknown source publication date'},
                   {'text': 'AfD cyberattack unrelated to region', 'time': alerts[0]['time']}]
        pushed = []
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"ok":true}'
        def urlopen(req, **kwargs):
            pushed.extend(json.loads(req.data)['events'])
            return Response()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
            root = Path(td); (root/'docs').mkdir(); (root/'state').mkdir()
            log = root/'state/intel-log.jsonl'
            log.write_text(json.dumps({'logged_at': now, 'type': 'osint', 'alerts': alerts})+'\n')
            with patch.multiple(m, INTEL_LOG=str(log), SKILL_DIR=td, STATE_DIR=str(root/'state'),
                                DOCS_DIR=str(root/'docs'), FEED_FILE=str(root/'docs/intel-feed.json')), \
                 patch.dict(os.environ, {'MAGEN_NO_PUBLISH': '1'}), \
                 patch('urllib.request.urlopen', side_effect=urlopen):
                m.main()
            feed = json.loads((root/'docs/intel-feed.json').read_text())
            self.assertEqual(feed['count'], 105)
            self.assertEqual(feed['events'][0]['ts'], now-30)
            self.assertEqual(len(pushed), 100)
            self.assertEqual(pushed[0]['ts'], now-30)
            self.assertEqual(pushed[-1]['ts'], now-30-99*60)

    def test_retired_timer_no_config_or_network(self):
        m = module('trump-countdown')
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
            self.assertEqual(m.main(), 0)

    def test_summary_rejects_old_collected_today(self):
        m = module('generate-summary')
        events = [{'type': 'osint', 'logged_at': time.time(), 'alerts': [
            {'text': 'Iran fresh source report', 'time': formatdate(time.time()-20, usegmt=True)},
            {'text': 'Iran old source report', 'time': '2026-04-07T00:00:00Z'}]}]
        result = m.extract_osint_highlights(events)
        self.assertEqual([x['text'] for x in result], ['Iran fresh source report'])


class PublicationTests(unittest.TestCase):
    def test_publish_is_scoped_retries_noop_and_fails_on_unavailable(self):
        def git(root, *args):
            return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.STDOUT).strip()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
            root = Path(td)/'repo'; remote=Path(td)/'remote.git'; root.mkdir()
            git(root, 'init', '-b', 'main'); git(root, 'config', 'user.name', 'Fixture'); git(root, 'config', 'user.email', 'fixture@example.invalid')
            git(root, 'init', '--bare', str(remote)); git(root, 'remote', 'add', 'origin', str(remote))
            (root/'feed.json').write_text('first'); (root/'other.txt').write_text('original')
            git(root, 'add', '.'); git(root, 'commit', '-m', 'seed'); git(root, 'push', 'origin', 'main')
            (root/'feed.json').write_text('new'); (root/'other.txt').write_text('unrelated')
            git(root, 'add', 'other.txt')
            publish(root, ['feed.json'], 'fixture feed')
            self.assertEqual(git(root, 'show', 'HEAD:other.txt'), 'original')
            self.assertEqual(git(root, 'diff', '--cached', '--name-only'), 'other.txt')
            # Locally committed but remotely pending must survive a no-input tick.
            (root/'feed.json').write_text('pending'); git(root, 'commit', '--only', '-m', 'pending', '--', 'feed.json')
            publish(root, ['feed.json'], 'retry')
            self.assertEqual(git(root, 'rev-parse', 'HEAD'), git(root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])
            git(root, 'remote', 'set-url', 'origin', str(Path(td)/'absent.git'))
            with self.assertRaises(RuntimeError):
                publish(root, ['feed.json'], 'must fail')


if __name__ == '__main__':
    unittest.main(verbosity=2)
