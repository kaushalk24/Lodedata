# Roadmap: extra features and AI

Status: **plan only**. Nothing in this document is built yet.

The rule stays the same as before: logging a set is **open exercise → + → ✓**, and no feature may add a step to it.
New features either run in the background, sit one tap away, or are opt-in.

Effort: **S** = a day or less, **M** = a few days, **L** = a week or more.

## 1. Quick wins (no AI)

| Feature | Why it matters | Effort |
|---|---|---|
| **Set types**: timed (plank 60 s), distance (farmer's carry 40 m), assisted (pull-up −20 kg), left/right for single-arm work | Today a plank logs "reps". Assisted machines get logged as positive weight, so a stronger lifter looks weaker | M |
| **Supersets and circuits**: link 2–3 exercises; saving one opens the next, and rest starts after the last | Common in the templates ("Burn Fat" is a circuit) and in Setgraph's own Shortcuts examples | M |
| **Warm-up ramp**: from today's working weight, suggest bar × 10, 50% × 5, 70% × 3, 85% × 1 with plates per side | Removes mental math before every heavy lift | S |
| **RPE / reps in reserve** as an optional chip | Better progression targets ("8 reps at RPE 7 → add weight") | S |
| **Dumbbell and machine steps per gym** (e.g. dumbbells in 2.5 kg steps, stack in 5 kg steps) | The target then suggests weights that exist at your gym | S |
| **Move or copy sets to another day**; edit a whole session at once | Fixes a day logged on the wrong date | S |
| **Exercise links**: a YouTube link or form cues per exercise | Quick form reminder without leaving the app | S |
| **Body measurements and progress photos**, stored only on the phone, with side-by-side compare | Weight alone misses recomposition | M |
| **Monthly and yearly recap card** (sessions, tonnage, PRs, most-improved lift) | Motivation, and something to share | S |
| **Strength levels** (e.g. bench 1.0× bodyweight = intermediate) on the Records view | Gives records context | S |

## 2. Smart features that run on the phone (free, offline)

These feel like AI but are statistics over your own log. They need no server, cost nothing and work offline.

| Feature | How it works | Effort |
|---|---|---|
| **Typo guard** | Before saving, compare with recent working weights. At 275 kg when you usually lift 27.5, ask "Did you mean 27.5?" | S |
| **Duplicate finder** | Fuzzy name matching flags pairs like *Forearm curls 1 / 2* or *Jm / Jm press* and offers a one-tap merge | S |
| **Learned rest** | Median real rest per exercise (your average is about 5 min, against a 2:45 default). Offers to set per-exercise timers | S |
| **Plateau and deload detector** | Trend line of estimated 1RM over the last 6 sessions. If it's flat or falling for 3 or more, suggest a deload week or a new rep range | M |
| **Load jump warning** | Weekly hard sets per muscle compared with your 4-week average: "Back volume is up 60% this week" | S |
| **What to train today** | Recovery map plus your split rotation picks the folder: "Chest shoulders: rested, last done 4 days ago" | S |
| **Goal projection** | Set "Bench 100 kg"; your trend estimates the date you'll hit it and whether you're on pace | M |
| **Quick text logging** | A text field that understands "8 at 60", "3x10 25" or "same again". Works with the iPhone keyboard's dictation button, so it covers voice too | M |

## 3. Claude-powered features (optional)

### How it would work

```
Phone (Overload PWA) ──► Cloudflare Worker (free tier) ──► Claude API
   ▲  your data stays here     holds the API key as a secret
   └── only what a feature needs is sent, and you see it first
```

- **The API key never goes into the app.** A tiny Cloudflare Worker (free tier: 100,000 requests a day) keeps the key as
  a secret, checks a private token stored on your phone, and forwards the request. A monthly spend limit in the
  Anthropic Console is the hard cap.
- **The AI is off until you turn it on.** Each feature shows what will be sent before it sends it. Nothing is sent in
  the background.
- **Send summaries, not the whole log.** For "ask your log", the search tools run on your phone and only the rows Claude
  asks for are sent.
- **Claude never saves anything by itself.** Parsed sets and plans come back as a preview that you confirm with ✓.
- **Model choice (your call).** The default is Claude Opus 5 (`claude-opus-5`), the most accurate. Simple jobs like
  parsing a sentence could run on Claude Haiku 4.5 at about a fifth of the cost.
- **Build notes:** structured JSON output for anything that becomes data, streaming for longer answers, prompt caching
  for the fixed instructions, and handling for the case where the model declines a request.

### Features, best value first

| # | Feature | What you'd do | Cost per use on Opus 5* | Effort |
|---|---|---|---|---|
| 1 | **Say or type your sets** | "Lat pulldown, 3 sets of 10 at 55, last one to failure". Claude returns the sets for you to confirm. Used when the offline parser can't read the sentence | ~$0.015 | M |
| 2 | **Weekly coach review** | Every Monday: volume per muscle compared with last week, PRs, stalled lifts, rest habits, and 3 concrete changes for next week | ~$0.06–0.15 | M |
| 3 | **Ask your log** | "When did I last bench 80?", "Is my shoulder press still improving?", "Which muscle am I neglecting?" Claude calls search tools that run on your phone | ~$0.05–0.10 per question | M |
| 4 | **Import from a photo or text** | Snap a notebook page, a Notes screenshot or a gym whiteboard, and get sets or a workout back | ~$0.04 per photo | M |
| 5 | **Personal plan designer** | Upgrades the offline designer: uses your history, recovery, equipment, time per session and any injuries you mention, then builds folders and targets | ~$0.10–0.20 per plan | M |
| 6 | **Exercise cleanup** | One pass over all your exercises: suggests merges, fixes typos ("Traingle", "Smithmaskin"), fills in muscles | ~$0.05, one-off | S |
| 7 | **Identify a machine from a photo** | Photo of an unfamiliar machine → exercise name, muscles and setup tips, added to your list | ~$0.03 per photo | S |
| 8 | **Form feedback from photos** (experimental) | 2–3 photos at key positions → cues to check. Clearly labelled as general guidance, not a coach | ~$0.05 | L |

\* Estimates at Opus 5 list prices ($5 input / $25 output per million tokens), before prompt caching, which lowers the
cost of the repeated instructions. Thinking tokens are billed as output, so harder questions cost more.

**Monthly estimate** for 4 sessions a week, using 1–3: about **$1–3 a month on Opus 5**, or well under $1 with the
cheaper model for parsing. There is no subscription: you pay Anthropic only for what you use.

### What we won't do with AI

- Chatbots on every screen, or AI-written motivational messages.
- Calls that happen without you asking.
- Automatic weight increases without your confirmation.
- Medical or injury diagnosis. If a note mentions pain, the app suggests seeing a professional.

### Before shipping any AI feature

Collect about 50 real phrases you'd actually say at the gym (from your own notes) and measure how often the parser gets
them exactly right. Ship only when it beats the offline parser and gets 95% or more right.

## 4. Bigger bets

| Feature | Notes | Effort |
|---|---|---|
| **Native iPhone shell** (Capacitor, reusing this code) | Unlocks what a web app can't: rest timer on the lock screen (Live Activity), notifications when rest ends with the phone locked, Apple Health, stronger haptics. Needs a Mac with Xcode. Installing on your own phone is free, but it has to be re-signed every 7 days. The App Store needs the $99/year developer program | L |
| **Encrypted sync** between phone, iPad and laptop | Cloudflare storage with end-to-end encryption from a passphrase only you know. No account | L |
| **Share a workout by link or QR code** | The workout is encoded in the link itself, so no server is needed | S |
| **Apple Watch logging** | Only after the native shell exists | L |

## 5. Suggested order

1. **Phase 1, data quality and speed:** set types, typo guard, duplicate finder, learned rest, warm-up ramp.
2. **Phase 2, training intelligence (offline):** plateau detector, load jump warning, what to train today, goal
   projection, supersets.
3. **Phase 3, AI (opt-in):** Worker proxy, then *say or type your sets* and the *weekly coach review*. After that:
   *ask your log*, *photo import*, *personal plan designer*.
4. **Phase 4, native and sync:** Capacitor shell for the lock-screen timer and Apple Health, then encrypted sync.

## Decisions needed

1. **AI budget and model:** are you OK spending roughly $1–3 a month? Opus 5 everywhere, or the cheaper model for
   parsing?
2. **Hosting:** a free Cloudflare account for the Worker (and for hosting the app itself).
3. **Native app:** do you have a Mac, and do you want the lock-screen timer badly enough to maintain an Xcode build?
