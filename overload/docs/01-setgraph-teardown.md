# Setgraph teardown: what the recording shows

Source: a 2 min 14 s screen recording of **Setgraph** (iOS), made on Mon 28 Sep 2026 between 10:30 and 10:32.
Timestamps below (`m:ss`) point into that recording. Each number in this document was read off a frame, and each
formula was checked against the numbers on screen.

## The model in one paragraph

Setgraph is an **exercise-centric notepad**. You never "start a workout". You open an exercise, tap +, and log a set.
Workouts are folders that group exercises, and an exercise can sit in several folders. Every analysis (history,
comparison, chart, 1RM, records, body map, today summary) is derived from one flat list of sets. That is why logging is
fast, and it is the core to keep.

## Visual language

| Element | Detail |
|---|---|
| Background | True black, grouped cards in `#1C1C1E`, 16 pt corners, hairline separators |
| Header | 44 pt circular buttons (gear, back, •••, share, filter), centred 17 pt semibold title |
| Tab bar | Floating pill: **Sets · Sessions · Body · Today**. Active tab gets a lighter pill and a green icon and label |
| Accent | Green for primary actions (New Workout…, +, ✓, New Session) |
| Metric colours | Sets red/pink · reps green · weight orange · volume cyan · exercise count blue · 1RM purple · records gold |
| Search | Floating rounded field above the tab bar ("Search or add", "Add or remove") |
| Sheets | Creation and settings open as bottom sheets with ✕ on the left and ✓ on the right |

## 1. Sets tab: My Workouts (0:01, 0:31, 1:41)

- Header: settings gear on the left; flame (streak) and **Edit** on the right.
- **My Workouts** card: `+ New Workout…` and `✨ New Custom Plan…` in green, then `My Exercises 59 ›`, then the folders
  with counts: Legs 13, Chest shoulders 12, Arms 20, Back 12. The folders total 57, so 2 exercises are in no folder.
- **Workout Templates**, collapsible, as a 2×2 grid: *Grow Your Upper Body* (Incline Bench Press, Seated Cable Row, Du…),
  *Burn Fat & Boost Endurance* (Goblet Squat, Kettlebell Swing, Dumbbell Push…), *Build Powerful Legs & Glutes*
  (Barbell Lunge, Leg Press, Leg Extension…), *Starting Strength* (Squat, Bench Press, Overhead Press, Dead…).
- **BUILDING YOUR WORKOUTS** tip card. Its title rotates between visits: *Organize by Program* (0:01),
  *Organize by Muscle Group* (0:49), *Organize by Workout* (1:41).

## 2. My Exercises (0:05–0:30)

- All 59 exercises, most recent first, with a relative time on the right: `3h ago`, `Yesterday`, `2d ago`, `4d ago`,
  `6d ago`, `1w ago`, `2w ago`, `1mo ago` … `11mo ago`, then an absolute `17/09/25` after a year. Exercises that were
  never logged show no time (Hack Squat, Jm, Seated Row, Plank).
- Floating **Search or add**. Typing shows, in order:
  1. `+ Create "<query>"`
  2. your matching exercises, with times
  3. **By Popularity**: library exercises with a line illustration, name, muscles ("Chest, Triceps, Shoulders"),
     a green **+** to add and a **(?)** for info.
- Matching is live and word-prefix based: `H` matches many, `Hd` matches *Tricep Pushdown (Rope)* plus library items,
  `Hdi` matches nothing but the Create row.

## 3. Workout folder (0:32–0:40, 1:40)

- Header: back, folder name, share, •••. Rows are the same exercise rows, sorted by recency.
- Bottom bar: a notes icon (the folder's description or plan), the **Add or remove** field, and a duplicate icon.

## 4. Design Your Plan (0:44–0:46)

- Sheet labelled *Powered by Setgraph AI*, with a **Guided** button.
- Training Goal: **Physique** ("Target the areas needed to achieve the body you want") or **Athletic Performance**
  ("Optimize your training to excel in your sport or activity"). **Generate Plan** stays disabled until a goal is picked.
  This is the AI feature that sits behind the subscription.

## 5. New Workout sheet (0:46–0:48)

✕ · *New Workout* · ✓. Green book icon. **Name** (placeholder "Lower Body, Monday, Triceps…", helper "Organize by
workout, muscle group, day of the week, etc."), **Description** ("Set a description or plan"), a colour row
(red, orange, yellow, green, pink, blue, purple, grey, multicolour), **Group** ("No Group", "Optional: Organize this
workout into a group").

## 6. Exercise detail: Sets (0:52–1:18)

- Header: back, exercise name, filter (≡), •••. View switcher: **Sets** (white pill with a label when active), then
  icons for **Chart**, **1RM** and **Records**.
- History is grouped by day, newest first. The day header reads `Thursday ›` inside the last week, otherwise
  `Sat, 19 Sep 2026 ›`.
- The newest day carries a **COMPARED TO PREVIOUS** card:

  | Metric | Value | Change | Bar colour |
  |---|---|---|---|
  | Sets | 3 | ▲ 0 (0%) | red |
  | Reps | 25 | ▲ 0 (0%) | green |
  | Volume (kg) | 447.5 | ▼ 15 (3.2%) | cyan |
  | kg/rep | 17.9 | ▼ 0.6 (3.2%) | orange |

  Check: Thursday = 12×7.5 (warm-up) + 6.5×27.5 + 6.5×27.5 = 447.5 kg over 25 reps, so 17.9 kg/rep. Sat 19 Sep =
  10×5 + 8×27.5 + 7×27.5 = 462.5 kg, so the change is −15 (−3.2%). **Warm-ups count** toward volume and reps.
- **Set row**: index · time (`6:59 AM`) · label badge (orange **W** = warm-up) · trophy for a PR · reps in green
  ("rep") · weight in orange ("kg") · chevron, with an optional note right-aligned underneath.
- **Half reps are allowed** (6.5, 7.5, 9.5).
- Bottom: a green **+** FAB and a smaller stacked-layers button next to it.
- The Shoulder Press history runs back to January 2026, about 100 sessions.

### Notes found in the history

`Seated on chair more upright`, `Standing`, `Drop set`, `Standing drop set`, `Not failure`, `1 min break standing`,
`Warm up`, `Dumbell`, `Change over`, `Light workout headache`, `Did machine press warm yo don't know weight and rep`,
`Warm up cult Vijaynagar machine`, `Basaweshwara cult`, `Should press machine change over`,
`Change over in chest press machine altered`.

Notes are doing three jobs here: set type (drop set, failure), **machine setup**, and **which gym**.

## 7. Set entry sheet (1:01–1:10)

- **Reps** field, prefilled from the last set (`6.5`) and shown selected with green handles, so the first key press
  replaces it. **−/+** steppers.
- **Weight** field (`27.5 kg`) with two stepper rows, **−1/+1** and **−5/+5**.
- Horizontally scrolling chips: **Label · Plates · Weight · KG · Now**.
- **Add note** field and a large green **✓**.
- A custom number pad (1–9, `.`, 0, ⌫), a keyboard toggle and a forward arrow.
- The **Label** picker: *Add Label…*, Warm-Up (orange), AMRAP (green), PR (yellow), Failure (red), None (✓). After a
  pick the chip turns orange and reads *Warm-Up*.
- Saving starts the **rest timer bar** above the tab bar: `◯ 2:44 Next Set ✕`, counting down from the default 2:45.

## 8. Chart (1:31)

Headline `6.5 rep 27.5 kg W` and `Last Set: 28/09/26, 10:31 AM`. Two lines: reps (green) and weight (orange), one
point per set. Toggles: **Last 2 Sessions | All** and **Sets | Stats**.

## 9. 1RM (1:35), purple

*1RM Settings*: **1 Rep Max: Off** and **f(x) Formula ›**, with the explainer "For some exercises, targeting a
percentage of your 1RM can help you reach your workout goals…".

## 10. Records (1:37), gold

- **Best Efforts**: Set Volume 807.5 kg, Session Volume 2450 kg.
- **Repetitions → Record**: `1–6: 95 kg`, `7–9: 85 kg`, `10–14: 35 kg`, `15–16: 7.5 kg`.
- Meaning: for each rep count *r*, the heaviest weight lifted for **at least** *r* reps, with runs of equal values
  merged into a range. The trophies agree: *6 rep 95 kg* (22 Mar) and *16 rep 7.5 kg* (10 Mar). The second one is a
  **warm-up**, so warm-ups count toward records as well.

## 11. Sessions tab (1:18)

Header **Duration** (left), *Sessions*, **Style** (right). An **All** filter chip. The empty state shows faded example
cards (*Strength Training 00:29*, *Tennis 01:31*, *Stair Climbing 00:10*) and the text "No Sessions: Add sessions to
track the duration of your activities". At the bottom: an activity picker (*Strength Training ⌃*) and **New Session**.

## 12. Body tab (1:20)

- Header: refresh, *Body*, **+**. A **Weight** row.
- Legend: *Just Trained* (red) and *Rested* (green). Orange sits in between but isn't in the legend.
- Front and back muscle map. **⚠ Unassigned Exercises 15** in orange.
- Muscle list with a dot and a time: Shoulders *11 secs ago*, Triceps *11 secs ago*, Back *3h ago*, Biceps *3h ago*,
  Hamstrings / Glutes / Quads *Yesterday* (orange), Chest *4d ago*, Forearms *3mo ago*, Adductors and Abductors
  *8mo ago*, Calves *17/09/25* (green).
- Inferred thresholds: red under 1 day, orange 1–3 days, green after that. A Shoulder Press set also lights up
  Triceps, so **secondary muscles count**.

## 13. Today tab (1:23–1:27)

- Header: calendar, share. A *Share your workout* tip ("Turn this session into an image card or caption-ready text").
- Week strip S…S, with 27 and 28 filled green (trained) and 28 outlined (selected).
- Stats: **Sets 8** (red), **Repetitions 68.5** (green), **Exercises 4** (blue), **Volume 5,080.75 kg** (cyan),
  **Duration --**, **Avg Rest 5m 22s** (orange), **Session Time 00:00**, **PRs 🏆 1**.
- **Set Details**: `Seated Row (Close): 3 sets: 9 rep 105 kg`, `Lat Pulldown: 2 sets: 7 rep 105 kg`,
  `Rare Delts: 12 rep 16 kg / 9 rep 45 kg`, `Shoulder Press: 6.5 rep 27.5 kg`. Identical sets collapse into "N sets".
- Check: sets 3+2+2+1 = 8; reps 27+14+21+6.5 = 68.5; volume 2835+1470+192+405+178.75 = 5,080.75 kg.
- *Duration* and *Session Time* are empty because no session was started. The day's timing data exists in the set
  timestamps but is left unused.

## 14. Settings (1:44–2:13)

| Item | Detail |
|---|---|
| Account | Sign-in |
| Plates Keyboard | *Gym (Default)*: 30 each of 2.5, 5, 10, 15, 20 and 25; *New…*; Starting Weights: Barbell 20 kg |
| Unit | Metric (kg/km) |
| Integrations | Apple Watch sync; Apple Health access |
| Shortcuts | Actions: Create Exercise, Record Set, Exercise. Examples: *Trio Superset* (Sit-Ups, Push-Ups, Pull-ups), *Squat Dropset* |
| Display | Theme: Match Device; **Notepad Mode: On** (keeps the screen awake) |
| Streaks | Workout goal: 3 workouts per week; Daily Congratulations: on |
| Record Celebrations | On |
| Workout Reminders | Remind after 4 days inactive |
| Default Interset Rest | Timer on, 2 min 45 s. Presets: Time Efficient 1 min, Build Muscle 2 min, Increase Strength 5 min. Article: *Understanding Interset Rest* |
| Help & Feedback, Version History | |
| **Pro Membership** | The subscription |

## Formulas (as implemented in `js/stats.js`)

| Metric | Formula |
|---|---|
| Set volume | reps × weight (plus bodyweight when the set is marked bodyweight) |
| Session volume | Σ set volume for the day, warm-ups included |
| kg/rep | session volume ÷ session reps |
| Compared to previous | latest day vs the day before it: absolute change and % of the previous value |
| Record for *r* reps | max weight over sets with reps ≥ *r*; equal neighbours merge into ranges |
| PR set | heavier than every earlier set with at least as many reps (never on the exercise's first day) |
| Avg rest | mean gap between consecutive sets in the day (gaps over 20 min count as a break) |
| Recovery colour | red < 24 h, orange < 72 h, green after that |

## What the data says about how this lifter trains

- **3 gyms**: Cult Rajajinagar, Vijayanagar and Basaveshwaranagar. Machines differ, so gym names end up in notes
  and even in exercise names ("Chest press rajajinagar").
- **Machine settings** are retyped as set notes over and over.
- **Duplicates and typos**: *Forearm curls 1 / 2*, *Jm / Jm press*, *Chest Press Machine / Chest press rajajinagar /
  Chest Press Iso Lateral Machine*, *Dumbell*, *Traingle*, *Smithmaskin*, *Baysian*, *Rare Delts*.
- **15 of 59 exercises have no muscles**, so the body map under-reports.
- **Half reps are common**, which is fine and should stay supported.
- **Real rest is about 5 min** (Avg Rest 5m 22s), well over the 2:45 default.
- Split: folders by body part, about 3–4 sessions a week.

These observations drive the improvements in [02-improvements.md](02-improvements.md).
