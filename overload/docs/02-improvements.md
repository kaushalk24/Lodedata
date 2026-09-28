# Making it better without making it heavier

The rule for every change: **keep the notepad core** (open exercise → + → ✓) and never add a step to logging a set.
Each improvement either removes typing, answers a question a lifter asks mid-set, or fixes something the recording shows
going wrong. Everything here is free, with no account, subscription or AI service.

✅ = built into Overload now. ◻️ = good next step.

## At the gym, between sets

| | Improvement | Why (evidence from the recording) |
|---|---|---|
| ✅ | **"Beat last time" target** in the set sheet: *Last time 8 × 25 kg → Try 9 × 25 (+1 rep)*. One tap fills it in. Uses double progression: add reps up to the top of your range (8–12 by default), then add the smallest weight step. | Progressive overload is the point of logging. Setgraph shows history but never tells you what to do next. |
| ✅ | **Live record badge**: the sheet shows *🏆 Record* while you type, before you save. Saving fires confetti and a gold toast. | Knowing it's a PR attempt before the set changes how you push. |
| ✅ | **Pinned exercise note** at the top of the exercise, for seat, pin and grip settings. | Notes like "Seated on chair more upright" and "Change over in chest press machine altered" are retyped on sets. |
| ✅ | **Gyms**: pick the gym you're at. Each set remembers it, each gym has its own bar and plates, and the exercise filter compares one gym at a time. | 3 Cult branches appear in notes and even in exercise names ("Chest press rajajinagar"). |
| ✅ | **Recent-note chips** under *Add note*. | The same notes ("Drop set", "Standing") are typed again and again. |
| ✅ | **Drop Set label** added next to Warm-Up, AMRAP, Failure. | "Drop set" and "Standing drop set" are typed as notes. |
| ✅ | **Visual plate calculator**: tap plates to load the bar, see both sleeves, and get per-side plates from any weight. Uses the gym's actual plate counts. | Setgraph has a plates keyboard but no picture of the bar. |
| ✅ | **Repeat last set** in one tap (the pill next to + shows exactly what it will log), with Undo. | The most common log is "same as last set". |
| ✅ | **Rest timer upgrades**: +30 s, per-exercise rest (squats 3:00, curls 1:30), a sound and vibration when rest ends, then a green *Go!* with overtime. Tapping the bar jumps back to the exercise. | Real average rest was 5m 22s against a 2:45 default, so one default doesn't fit every lift. |
| ✅ | **Backdate a set** from the *Now* chip. | "Did machine press warm yo don't know weight and rep" shows sets get logged after the fact. |
| ✅ | **Done-today ticks** and *Last: 8 × 25 kg · 3 sets* under each exercise in a workout folder. | At the gym the question is "what's left, and what did I lift last time?" |

## Understanding progress

| | Improvement | Why |
|---|---|---|
| ✅ | **Weekly sets per muscle** on the Body tab (primary = 1, secondary = 0.5, warm-ups excluded) with a 10–20 guide. | Recency alone ("3h ago") doesn't tell you if a muscle got enough work this week. |
| ✅ | **Recovering** added to the legend and a **muscle page** listing the exercises that hit it. | The recording's legend explains red and green but not the orange. |
| ✅ | **Auto duration** on Today from the first and last set, and **Session Time** from the Sessions tab. | Today showed *Duration --* and *Session Time 00:00* even though every set has a timestamp. |
| ✅ | **Stats chart**: estimated 1RM and session volume per session, with change %. | The *Sets* chart is noisy across many sessions. |
| ✅ | **1RM percentage table** (100% → 50% with approximate reps), 5 formulas. | Setgraph's 1RM screen is only a toggle and a formula picker. |
| ✅ | **Records you can tap**: jump to the exact set, highlighted. Adds heaviest set, most reps, best e1RM. | |
| ✅ | **Streak heatmap** (17 weeks) and "N more workouts this week". | Setgraph shows a flame with no history. |
| ✅ | **Bodyweight log with chart**, also used for pull-ups and dips (*Bodyweight +* chip). | |

## Keeping the data clean

| | Improvement | Why |
|---|---|---|
| ✅ | **Muscle guessing** from the exercise name (`Jm press` → triceps, `Rare Delts` → shoulders, `Baysian curl` → biceps). | 15 of 59 exercises were *Unassigned*. |
| ✅ | **Merge exercises**: move all sets of one exercise into another. | *Forearm curls 1 / 2*, *Jm / Jm press* and gym-specific duplicates split the history. |
| ✅ | **Rename** and a one-screen **Assign Muscles** list. | Typos: *Dumbell*, *Traingle*, *Smithmaskin*. |

## Free forever

| | Improvement | Why |
|---|---|---|
| ✅ | **Offline plan designer** replacing *Setgraph AI*: goal × days/week × equipment × level produces a real split (Full Body, PPL, Upper/Lower) with sets, reps and rest, saved as folders. | The AI plan is the paywalled feature, and a rules engine does this job well. |
| ✅ | **Your data, your files**: JSON backup and restore, CSV export, and **CSV import** with auto-detected columns (Setgraph, Strong, Hevy, spreadsheets). Re-importing skips duplicates. | You need your years of history to move in with you. |
| ✅ | **Share card**: a 1080×1350 image of the day plus caption-ready text. | Same as Setgraph, without the Pro upsell. |
| ✅ | **PWA**: add to Home Screen, full screen, works offline, keeps the screen awake (Notepad Mode). | No App Store, and no $99/year Apple developer fee just to run your own app. |

## Added in v1.1

Each one follows how the leading apps do it (Hevy, Strong, Fitbod, StrongLifts), kept to one extra tap at most.

| Feature | How it works | Modelled on |
|---|---|---|
| **Set types** | Weight & reps, Bodyweight (+kg), Assisted (kg of help, stored as negative load), Timed (typed like a timer: 130 = 1:30) and Distance (m). Picked from the type chip in the set sheet, guessed from the name (Plank is timed, Farmer's Carry is distance), and never overriding what your history shows | Hevy's exercise types |
| **Left / right** | One-arm and one-leg exercises log each side; the sheet alternates L and R, targets compare side with side, and switching sides isn't counted as rest | |
| **Supersets and circuits** | Workout ••• › Create superset. After a set the next exercise opens by itself; the rest timer only runs after the last one | Hevy's smart superset scrolling |
| **Warm-up ramp** | 40% × 5, 60% × 5, 80% × 3 of the working weight (plus the empty bar for barbells), rounded to loadable weights with plates per side. Tap ✓ per set | Hevy's default formula; Strong/StrongLifts empty-bar sets |
| **RPE** | Optional one-tap row (6–10, half steps), off by default. Easy sets (≤ 7) get a weight jump next time; all-out sets (9.5–10) are matched first | Hevy's RPE column |
| **Measurements and photos** | Body fat and tape measurements (cm or in) with charts; progress photos stored only on the phone, with compare-to-first | Strong's Measure tab |
| **Typo guard** | On save, a weight 2.2× your usual (or a slipped decimal) asks "275 kg? Did you mean 27.5?" with Use / Keep | |
| **Duplicate finder** | Flags names that are the same exercise (typos, plurals, "curls 1/2", "Jm / Jm press"), never pairs done together on two days; one-tap merge | Strong's Transfer Exercise Data |
| **Learned rest** | Median real rest per exercise (back-to-back sets only). Offered in the exercise rest menu and in Settings with Apply / Apply to all | |
| **Plateau detector** | No better estimated 1RM for 4 sessions over 2+ weeks → "Stalled" tag and a lighter-week suggestion (~10% less) | e1RM-stall detection in progression apps |
| **Up next** | Picks the workout whose muscles are most recovered (72 h), oldest first; suggests rest if everything is sore | Fitbod's recovery model |
| **Goal date** | Set a 1RM goal; a trend line through the last 120 days projects the date | |
| **Type or say it** | "8 at 60", "3x10 25", "185x5x3", "10, 9, 8 at 25", "60 for 8", "same again", spoken numbers, labels, RPE and sides, with a preview before saving | Gym shorthand (3x8@135, 185x5x3) |

## Next steps, in order of value

The full plan, including optional AI features, is in [03-roadmap.md](03-roadmap.md).

1. ◻️ **Supersets**: link 2–3 exercises so saving one opens the next, and rest starts after the last.
2. ◻️ **RPE / reps in reserve** as an optional chip, feeding smarter targets.
3. ◻️ **Warm-up ramp** generator from the working weight (bar × 10, 50% × 5, 70% × 3, 85% × 1) with plates.
4. ◻️ **Home-screen widget / lock-screen timer**. This needs a native wrapper (Capacitor) for a live activity.
5. ◻️ **Sync between devices** without an account: export to iCloud Drive and import, or an optional self-hosted
   sync endpoint.
6. ◻️ **Apple Health**: write workouts and read bodyweight. Needs a native wrapper, since web apps can't reach HealthKit.

## What we deliberately did not add

- A "start workout" mode with a session screen. It adds a step before every log and fights the notepad model.
- Social feeds, coaching chat and AI. They cost money to run and add noise.
- Accounts. Data stays on the phone, with easy backups.
