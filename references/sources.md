# Iran-Israel Alert Sources — Full Reference

## Tier 1: Official & Wire Services (Confirmed/Authoritative)

| Source | X Handle | Type | Speed | Notes |
|--------|----------|------|-------|-------|
| IDF Spokesperson | @IDF | Official | Fast | Official Israeli military. English account. |
| Pikud HaOref (Home Front Command) | N/A | API | Instant | `oref.org.il/WarningMessages/alert/alerts.json` — real-time siren data |
| Israel PM Office | @IsraeliPM | Official | Fast | Government statements |
| AP Breaking | @AP | Wire | Fast | Gold standard verification |
| Reuters | @Reuters | Wire | Fast | Gold standard verification |
| Iran's IRNA (English) | @IrnaEnglish | State media | Moderate | Official Iranian narrative; useful for confirming Iran acknowledges events |
| Fars News (English) | @FarsNews_Agency | State media | Moderate | IRGC-affiliated; useful for Iranian military claims |

## Tier 2: OSINT & Fast Analysts (Usually Accurate, Verify)

| Source | X Handle | Speed | Reliability | Bias/Notes |
|--------|----------|-------|-------------|------------|
| Sentdefender | @sentdefender | Very fast | Good | Global conflict OSINT. One of the fastest. Sometimes posts unverified early. |
| OSINT Defender | @OSINTdefender | Very fast | Good | Companion to sentdefender. Similar quality. |
| OSINTtechnical | @OSINTtechnical | Fast | Very good | Prioritizes accuracy over speed. Satellite imagery analysis. |
| Aurora Intel | @Aurora_Intel | Fast | Good | Flight tracking + OSINT. Great for detecting military aviation movements. |
| Israel Radar | @IsraelRadar_com | Very fast | Good | Focused on Israel security. Hebrew + English. |
| Itay Blumental | @no_itay | Fast | Very good | Ynet military correspondent. Well-sourced. |
| Barak Ravid | @BarakRavid | Fast | Very good | Axios/Walla diplomatic correspondent. Breaks diplomatic news first. |
| Seth Frantzman | @sfrantzman | Moderate | Very good | JPost defense editor. Deep Iran/Turkey/Iraq expertise. |
| Joe Truzman | @JoeTruzworthy | Fast | Good | FDD Long War Journal. Gaza militant groups + Iran proxies. |
| Fadi Alkadiri | @Faboron | Fast | Good | OSINT aggregator, Middle East focus. |
| Intel Crab | @IntelCrab | Fast | Good | Global OSINT. Active during escalations. |
| Hananya Naftali | @HananyaNaftali | Fast | Moderate | Pro-Israel bias. Fast but occasionally sensational. |
| Iran International | @IranIntl | Fast | Good | London-based, Persian-language. Anti-regime but well-sourced on Iranian military. |
| Amichai Stein | @AmichaiStein1 | Fast | Very good | KAN News diplomatic correspondent. |

## Tier 3: Aggregators & Community (Cross-Reference Only)

| Source | X Handle | Notes |
|--------|----------|-------|
| War Monitor | @WarMonitors | Fast but lower verification standard. Cross-reference. |
| Conflict News | @ConflictNews | Aggregator. Sometimes early, sometimes wrong. |
| BNO News | @BNONews | Fast breaking news. Generally reliable but verify. |
| Middle East Eye | @MiddleEastEye | Qatari-funded. Good coverage, editorial bias. |

## Oil & Commodities (Conflict Signal)

Oil is the fastest financial market signal for Iran/Israel escalation. A real strike on Iranian oil infrastructure or Strait of Hormuz disruption sends crude up 5-15% within minutes.

### Free API

| Source | Endpoint | Auth | Update Freq | Weekend |
|--------|----------|------|-------------|---------|
| **OilPriceAPI demo** | `api.oilpriceapi.com/v1/demo/prices` | None | 5 min | Returns last data |

Returns: WTI, Brent, Natural Gas, Gold, EUR/USD, Heating Oil, Gasoline, Diesel — all with `change_24h` %.

Rate limit: 20 requests/hour (plenty for monitoring).

### Weekend Oil Trading (when NYMEX is closed)

NYMEX futures trade Sunday 6pm – Friday 5pm ET. On weekends:

| Platform | URL | Notes |
|----------|-----|-------|
| **IG.com** | `ig.com/en/commodity-trading/oil` | Weekend oil CFDs. Free demo account for API access. |
| **Spreadex** | `spreadex.com` | Weekend trading available |
| **City Index** | `cityindex.com` | Weekend oil markets |

### Spike Thresholds

| Change | Interpretation |
|--------|---------------|
| <3% | Normal volatility |
| 3-5% | Elevated — check OSINT for cause |
| 5-10% | **High alert** — likely real event (strike, Hormuz threat) |
| >10% | **Major event** — confirmed large-scale attack or supply disruption |

### What to Watch

- **WTI & Brent** — direct Iran/Gulf conflict proxy
- **Gold** — safe haven flight (spikes on any war fear)
- **Natural Gas** — less direct but moves on broad energy disruption
- **USD/ILS** (Israeli Shekel) — weakens on Israel security events

## Prediction Markets

| Platform | API | Auth | Iran/Israel Activity | Notes |
|----------|-----|------|---------------------|-------|
| **Polymarket** | `gamma-api.polymarket.com` | None (public) | **High** — multiple active markets | Best source. No auth needed. Prices = probabilities. |
| **Kalshi** | `api.elections.kalshi.com/trade-api/v2` | API key (free account) | Low — CFTC limits geopolitical | US-regulated. Check but don't rely on. |

### Polymarket Active Markets (auto-discovered)

The script dynamically discovers markets by fetching all open markets and filtering by keywords.
No hardcoded slugs needed — new markets are automatically picked up.

Browse current markets: `https://polymarket.com/predictions/israel-strike-iran`

### How to Read Prediction Markets

- **Price = probability.** 0.25 means the market thinks 25% chance.
- **Sudden spike** (e.g. +15% in an hour) = smart money moving on intel. Often precedes news by 10-30 min.
- **Volume surge** = increased conviction. Check `volume` and `volume24hr` fields.
- **Compare to baseline.** Know the normal price range so you can spot anomalies.
- **Cross-reference with OSINT.** Price spike + OSINT chatter = high confidence something is happening.

### Kalshi Notes

- Requires account + API key for most endpoints
- WebSocket available for real-time: `wss://api.elections.kalshi.com/trade-api/ws/v2`
- Series tickers for geopolitical events vary; search `/events?status=open` with keywords
- Much less liquid than Polymarket for these markets

## Live Maps & Dashboards

| Source | URL | Notes |
|--------|-----|-------|
| Liveuamap (Israel) | https://israelpalestine.liveuamap.com | Real-time conflict map |
| Liveuamap (Iran) | https://iran.liveuamap.com | Iran-specific events |
| Pikud HaOref Alert Map | https://www.oref.org.il/ | Official siren map |
| CSIS Missile Threat | https://missilethreat.csis.org | Missile program tracking |

## RSS Feeds

```
# Israeli news
https://www.timesofisrael.com/feed/
https://www.jpost.com/rss/rssfeedsheadlines.aspx
https://www.israelnationalnews.com/rss

# Iran-focused
https://www.iranintl.com/en/feed
https://en.mehrnews.com/rss

# Regional
https://english.alarabiya.net/tools/rss
https://english.aljazeera.net/xml/rss/all.xml

# Wire services
https://rss.app/feeds/v1.1/tDtfXZdv7mFClcRh.xml  (AP top headlines)
```

## Telegram Channels

| Channel | Focus | Reliability |
|---------|-------|-------------|
| @aharonyediot | Aharon Yediot — Hebrew breaking news/OSINT | ⭐ HIGH (user-verified) |
| @RedAlertIsraelWarning | Pikud HaOref siren mirror | |
| @CensoredMen | Fast conflict updates |
| @inaboron | Hebrew military updates |
| @Iran_Intel | Iran OSINT |
| @MilitaryNewsEN | General military news |

## Key Context for Interpretation

- **Iran uses proxies**: Hezbollah, Houthis, Iraqi militias may signal Iranian involvement without direct attribution
- **"Sources say" from Israeli media** often = IDF/Mossad deliberate leaks
- **IRGC Telegram channels** often confirm strikes 30-60 min after they happen
- **Flight tracking** (Aurora Intel, Flightradar24) can detect military ops before official confirmation
- **Seismic data** can confirm large explosions — EMSC (European-Mediterranean Seismological Centre)
