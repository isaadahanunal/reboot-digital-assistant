# Reboot — Personalized Digital Well-Being Coach

Reboot reads the screen time you actually had — pulled from your device, not typed into a form —
and turns it into a daily digest and a realistic 7-day plan for reducing unnecessary screen use.

It is **local-first**: measurement, storage and aggregation happen on your machine. The only
outbound request in the entire project is the coach call you press yourself, and it carries
derived numbers, never a raw activity log.

```
device agent ──▶ local SQLite ──▶ deterministic aggregation ──▶ minimised payload
                                                                      │
                                                          consent gate + safety gate
                                                                      │
                                                          Gemini (structured JSON)
                                                                      │
                                                    guardrail check → repair pass → UI
```

---

## Run it in three commands

```bash
cd reboot
cd ui && npm install && npm run build && cd ..    # build the React UI (first time only)
./run.sh                                          # http://127.0.0.1:8765
```

`run.sh` builds the UI for you if `ui/dist` is missing, so the two-step form above is only needed
when you want to see the build output. Front-end development runs against the same API:

```bash
cd ui && npm run dev        # http://localhost:5173, proxies /api to the running server
```

The first launch walks you through a three-step setup — your goal, where the numbers come from, and
the coach engine plus its permission. Every step is skippable and none of it is a popup: skipping all
three still lands you in a working app.

Give it a Gemini key one of two ways (the setup flow also asks for it):

```bash
cp .env.example .env        # then set GEMINI_API_KEY=... and restart ./run.sh
```

or open <http://127.0.0.1:8765> and use the **Settings** page in the sidebar to paste it —
that stores it in `data/config.json` with mode `0600`. Resolution order is
**exported env var → `.env` → settings dialog**, and the dialog tells you which one is currently
winning so you never type into a field that a `.env` silently overrides.

Then press **Generate today's digest**.

Without a key the app still runs end to end in **offline rule-based mode**, clearly labelled as
"not AI-generated" everywhere it appears.

### Use your own real usage instead of the demo

Nothing here needs a terminal. Open **Settings → This computer** and press **Start recording**, or turn
it on during the first-run setup. The sampler runs as a background thread inside the local server, so it
keeps recording after you close the tab and starts again with the server.

It samples the frontmost application every few seconds, closes a stretch when you switch away, and drops
anything while the machine has been idle for more than two minutes so idle time is never billed as screen
time. Browser host names are a separate opt-in switch — `youtube.com`, never the full URL, the page title
or its content.

**Reboot measures the computer it runs on, and nothing else.** Phone import and remote-device pairing
were removed on purpose: each was a data path whose accuracy could not be verified from here, and a
promise the prototype could not keep. One machine, measured properly, beats three measured vaguely.

### Keeping it recording

Measurement needs a process running — no design avoids that, since the numbers come from sampling the
operating system. The collector lives inside the Reboot server, so **while `run.sh` is running, it is
recording**, whether or not a browser tab is open. Close the server and there is simply a gap in the
day; nothing is lost retroactively, and nothing is collected behind your back.

Three ways to keep it up, in increasing order of permanence:

```bash
./run.sh                                   # a terminal window you leave open
nohup ./run.sh > /tmp/reboot.log 2>&1 &    # detached from the terminal
```

For always-on, macOS has a LaunchAgent template in `deploy/com.reboot.coach.plist` — edit the path,
copy it to `~/Library/LaunchAgents/`, `launchctl load` it, and Reboot starts at login and restarts if it
crashes. Uninstalling is one `launchctl unload`.

Only one collector may run at a time. A second server refuses to record and says so, because two
samplers writing to one database double-count the same screen time and silently inflate every number the
coach reasons about (`data/collector.lock`).

### Verify everything works

```bash
python3 tools/selftest.py          # 32 checks: measurement, privacy, safety, prompts, pipeline
python3 tools/selftest.py --live   # additionally makes a real model call
```

---

## Why a PWA plus a device agent, and not "just a mobile app"

| Route | Can it read real screen-time data? | Verdict |
|---|---|---|
| Web page alone | No. Browsers have no API for OS-level app usage, by design. | Cannot meet the brief |
| Android native | Yes, via `UsageStatsManager` with a special permission | Works, but Android only |
| iOS native | No. Screen Time is only readable inside Apple's on-device `DeviceActivity` sandbox; an app cannot export it. | Blocked by the platform |
| **PWA + device connectors** | **Yes, per platform** | **Chosen** |

So "one app for everything" is not actually available on iPhone, and "a website" cannot see usage
anywhere. Reboot separates the two concerns instead: **one coach UI** (a responsive PWA that
installs to the home screen on Android and iOS and to the dock on desktop) and a **pluggable
connector layer** that supplies measurements per platform — the local agent for macOS/Windows/Linux,
file import for adb dumps and third-party tracker exports, and a documented path for a native Android companion.
That also keeps the personal data on the device where it was collected.

---

## Project layout

```
backend/
  config.py       settings + key storage (0600, never sent to the browser)
  models.py       pydantic schemas
  store.py        local SQLite, plus the audit trail of what was sent
  taxonomy.py     app/domain → category, user-correctable
  aggregate.py    raw sessions → the deterministic feature set (all arithmetic lives here)
  privacy.py      redaction, pseudonymisation, consent-gated payload construction
  safety.py       crisis gate, clinical/overclaim/judgement detector, confidence labelling
  prompts.py      every prompt on one architecture (role/goal/context/constraints/style/output),
                  annotated with technique and justification
  coach.py        orchestration: measure → minimise → generate → check → repair → store
  collector.py    the in-process sampler the interface starts and stops
  probes.py       the only code that touches the OS: frontmost app + idle time
  ingest.py       one normalisation path into the local database
  llm/            gemini (primary) · anthropic (secondary) · offline rule-based · router
agent/
  device_agent.py standalone sampler for a second machine, zero dependencies
  demo_seed.py    reproducible 8-day demo history through the real ingest path
  import_usage.py phone screen-time export importer
ui/               React + Vite front end (PWA)
  src/pages/      Onboarding · Today · Plan · Check-in · Privacy · Prompts · Settings
  src/components/ chart, bar list, coach output, guarded generate button, theme control
  dist/           build output — this is what the server serves
tools/selftest.py 32 end-to-end checks
REPORT.md         the hackathon write-up: prompts, techniques, ethics
```

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/ingest` | local ingest (used by the demo seeder) |
| `GET/POST /api/collector/status\|start\|stop` | control the sampler from the UI |
| `GET /api/metrics?date=` | deterministic daily metrics + week rollup |
| `POST /api/coach/daily` · `/api/coach/weekly` | generate a digest / plan |
| `POST /api/checkin` | adherence, which feeds the next plan |
| `GET /api/privacy/preview` | exactly what would be sent, before sending |
| `POST /api/privacy/erase` | delete everything, immediately |
| `GET /api/prompts` | the app serves its own prompts |

## Chat

The **Chat** tab is the same coach in conversation. It reuses `SYSTEM_COACH` unchanged — the persona and
every prohibition from the digest pipeline — and adds only turn-taking rules, because free text is where
a user can ask the leading questions the safety rules exist for ("so am I addicted?"). Ask it that and it
declines the label and gives you the comparison instead: what you said you wanted, against what the
numbers show.

Each turn carries the same minimised, consent-gated payload the digest gets, plus the headline of your
last digest and your current plan so the conversation does not contradict its own advice. The crisis gate
runs on what you type **before** any network call — and a message that trips it is never written to the
chat history, because storing it would hand it back to the model on the next turn and quietly undo the
gate one message later.

With the AI coach switched off, chat says plainly that it cannot hold a conversation rather than faking
one from templates.

## Interface notes

One React codebase serves phone and desktop: a sidebar on wide screens becomes a five-item bottom bar
under 900px (Settings moves to the top bar to keep it at five), with safe-area padding for notched
devices. Light and dark are both deliberate palettes
rather than an inversion, and the theme control has three states — Light, System, Dark — so a user who
picks one can hand the decision back to their OS. Add `?theme=light` or `?theme=dark` to the URL to
force one, which is handy when demoing both.

Interaction rules held throughout: every target is at least 44×44px with 8px between neighbours, body
text never drops below 12px, focus rings are restyled but never removed, status is never carried by
colour alone (every badge and notice pairs colour with an icon and a label), and all motion is disabled
under `prefers-reduced-motion`. There are no modal dialogs and no `confirm()` popups — destructive
actions arm themselves in place and disarm after five seconds.

## Model notes

Default is **`gemini-3.6-flash`** with `thinkingLevel: "low"`. Measured against this project's own
prompts: low thinking answers in ~6s versus ~35s, produces the same schema-valid output, and cited no
ungrounded numbers — the digest prompt already carries its reasoning procedure explicitly, so there
is little left for the model to work out on its own. Raise it with `REBOOT_GEMINI_THINKING=high`.

Wall-clock latency on the free tier is genuinely variable (6s and 45s observed for the *identical*
request with identical token counts), so the UI shows a live elapsed counter rather than pretending
generation is fast. Google also retires models on its own schedule — if a call 404s, run
`python3 tools/list_models.py` and pin a current one via `REBOOT_GEMINI_MODEL`.
