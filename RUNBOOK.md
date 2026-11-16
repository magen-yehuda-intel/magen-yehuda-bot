# Magen operations runbook

Collection = watcher daemon + 6 scheduled jobs. API + Table DB run in Azure RG
`magen-yehuda-intel` (container app `magen-yehuda-api`); dashboard is GitHub Pages
(`docs/`, deployed by Actions on push). No job needs an AI agent.

**Only one host may run collection at a time** — both would post to Telegram.

## Hosts

| Host | Role | Supervisor |
|---|---|---|
| Mac (`~/.openclaw/workspace/skills/iran-israel-alerts`) | current primary | launchd `com.openclaw.iran-israel-watcher` + crontab lines tagged `# magen` (gated by `~/.hermes/bin/host-guard --check`) |
| Dell WSL (`ssh -p 2222 idans@192.168.50.98`, same path) | standby; units installed, not enabled | systemd `--user` units from `deploy/systemd/` |

Every scheduled job runs through `scripts/run-job.sh <job>`. It cds into the repo,
puts `.venv/bin` (then `/opt/homebrew/bin` and `/usr/local/bin`, if present) at the front of
PATH, and appends output to the job's log in `state/`.

## Jobs

| Job (`run-job.sh …`) | Schedule | Publishes | Needs (names only) |
|---|---|---|---|
| `watcher` (`realtime-watcher.sh`) | always on | Telegram, API push, Table DB, `docs/live-events.json` git push | config `telegram_bot_token`, `outputs[].chat_id`, `api_key`; `secrets/nordvpn-auth.txt` (Oref proxy), `secrets/firms-map-key.txt`, `secrets/acled-creds.txt`, `secrets/aisstream-key.txt`; Azure credential for the DB (`az login`, or `AZURE_TABLE_CONN` built from `secrets/azure-table-conn.txt`) |
| `hourly-report` | `0 * * * *` | Telegram (map, summaries, GIF) | `telegram_bot_token`, `outputs`, `firms-map-key` |
| `export-feed` | `*/5` | git push `docs/intel-feed.json`, API `/api/push/intel` | `api_key`, git credential |
| `fr24` | `*/2` | git push `docs/fr24-cache.json` (pathspec commit) | git credential |
| `enrich-intel` | hourly | Table DB | Azure OpenAI (`az login`, dev tenant `dc617093-…`) |
| `generate-brief` | `*/30` | git push `docs/brief.json` | Azure OpenAI (`az login`, dev tenant) |
| `sitrep` (`post-telegram.sh --force`) | `0 */2 * * *` | Telegram | `telegram_bot_token`, `telegram_chat_id` |
| `rotate-logs` | `15 * * * *` | — | — (size > 5 MB → gzip to `state/logs/`, keep 3; `intel-log.jsonl` is trimmed to the last 48 h) |

Git credential: set the repo's `credential.helper` to `!gh auth git-credential`, with
`gh auth switch -u idanshimon`. Python deps: `python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt`.

## Status checks

```bash
bash ctl.sh status                       # launchd / systemd / pgrep aware
launchctl list com.openclaw.iran-israel-watcher        # Mac
systemctl --user status magen-watcher; systemctl --user list-timers 'magen-*'   # Linux
curl -s https://magen-yehuda-api.blackfield-628213bb.eastus.azurecontainerapps.io/api/health | jq .watcher
git log origin/main -5 --format='%h %an %s'           # feed/fr24 commits arriving?
tail state/feed-export.log state/hourly-report.log
```

`watcher.last_push_age_s` should stay below 120. Note that `/api/health` reports
`degraded` while the storage account blocks writes (`db.ok=false`).

## Moving collection between hosts

Mac → Linux:
1. On the Linux host: `git pull`, `bash deploy/systemd/install.sh`.
2. On the Mac: back up the crontab, run `launchctl bootout gui/$(id -u)/com.openclaw.iran-israel-watcher` (keep the plist), and comment out the `# magen` crontab lines.
3. On the Linux host: `bash deploy/systemd/install.sh --enable`.

Rollback (Linux → Mac):
1. On the Linux host: `systemctl --user disable --now magen-watcher 'magen-*.timer'`.
2. On the Mac: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.openclaw.iran-israel-watcher.plist`, then uncomment the `# magen` crontab lines.

## Known issues

- **Pikud HaOref is unreachable from both hosts.** It returns 403 directly. The configured `il66.nordvpn.com` proxy no longer resolves (NXDOMAIN). Live NordVPN IL proxies (`il9x.proxy.nordvpn.com:89`) connect, but CloudFront returns 403 for their IPs. The Azure API's own Oref poller is the only Oref source until an Israeli residential proxy is added in `secrets/proxy-override.txt`.
- Table storage AuthorizationFailure: the storage account's public network access is disabled, so every DB write fails. The failures are logged and do not stop jobs.
