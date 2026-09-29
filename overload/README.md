# Overload

A free, offline-first workout tracker modelled on Setgraph's fast "exercise notepad" logging, with the paid parts
rebuilt to run on your phone. No account, no subscription, no server.

- **Sets**: workout folders, My Exercises with a 130-exercise library, templates, and an offline plan designer.
- **Exercise**: history grouped by day with *Compared to previous*, a chart, 1RM with a percentage table, and records.
- **Set entry**: custom keypad prefilled from your last set, a "beat last time" target (RPE-aware), a live PR badge,
  labels, warm-up ramp, plate calculator, set types (weight, bodyweight, assisted, timed, distance, left/right),
  kg/lb, backdating, a typo guard, and "type or say it" logging.
- **Smart, offline**: Up next (most recovered workout), plateau detection, goal dates, learned rest times and a
  duplicate finder. Supersets and circuits move you to the next exercise automatically.
- **Sessions**: timed activities such as strength training, tennis or a run.
- **Body**: recovery map, weekly sets per muscle, bodyweight, measurements and progress photos (kept on the phone).
- **Today**: week strip, day stats, set details, calendar and a share card.

See [docs/01-setgraph-teardown.md](docs/01-setgraph-teardown.md) for the screen-by-screen analysis,
[docs/02-improvements.md](docs/02-improvements.md) for what was improved and why, and
[docs/03-roadmap.md](docs/03-roadmap.md) for planned features and optional AI.

## Run it

It's plain HTML, CSS and JavaScript modules, so there's no build step. Modules need to be served over HTTP:

```sh
cd overload
npx serve .            # or: python3 -m http.server 5173
```

Open the printed address. On first launch, tap **Try demo data** to explore with 16 weeks of sample history, or
**Log first set** to start clean.

## Put it on your phone (free)

The app needs nothing but free static hosting: no account, no server and no AI service. GitHub Pages hosts it from
this repository.

1. **Publish (once):** on GitHub open the repository's *Settings → Pages*. Under *Build and deployment* choose
   *Deploy from a branch*, pick the branch that holds this code and the `/ (root)` folder, then *Save*. After a minute
   the app is live at **https://kaushalk24.github.io/Lodedata/overload/** (the site root forwards there).
2. **iPhone:** open that link in Safari → Share → **Add to Home Screen**. It runs full screen and works offline.
3. **Android:** open it in Chrome → menu → **Install app**.

Worth knowing on iPhone:

- **Log in the Home Screen app, not a Safari tab.** They keep separate data.
- **Your log lives only on the phone.** Removing the app from the Home Screen can erase it, so save a backup from
  *Settings → Import & Export* now and then (My Workouts reminds you after 30 days). Progress photos aren't in backups.
- **Updates install themselves.** Every push to the published branch goes live; the app downloads the new version in
  the background and switches to it the next time it starts (Settings shows the version).

### Changing the code

Edit any file, then run `npm run stamp` in `overload/` before committing. It writes the file list and version into
`sw.js`, so phones fetch the whole new version at once (the tests fail if you forget).

## Bring your history

*Settings → Import & Export → Import CSV from another app* reads CSV exports from Setgraph, Strong, Hevy or a
spreadsheet. Columns are detected (exercise, date, time, reps, weight, note, set type) and you can adjust them before
importing. Importing the same file twice doesn't create duplicates.

## Tests

```sh
cd overload && npm test      # or `node --test` from the repo root
```

The tests cover the analytics against the exact numbers in the recording, plus the planner, CSV import/export,
date parsing, muscle guessing, the typed-set parser, the smart features, and that `sw.js` caches every file.

## Layout

```
overload/
  index.html, manifest.webmanifest, sw.js   app shell, install metadata, offline cache
  css/app.css                               tokens (dark + light) and components
  js/
    util.js      escaping, units, dates, CSV            stats.js    records, PRs, 1RM, plates, progression, recovery, streaks
    smart.js     typo guard, duplicates, learned rest,  parse.js    typed / dictated set logging
                 plateau, goal date, up next, warm-up
    library.js   exercises, muscles, templates          planner.js  offline plan designer
    store.js     state, IndexedDB, mutations            dataio.js   CSV import/export, demo data
    ui.js        navigation, sheets, dialogs, toasts    timer.js    rest timer
    chart.js     SVG chart                              bodymap.js  SVG muscle map
    screens/     home, exercises, exercise, setentry, flow (supersets), sessions, body, today, settings
  tests/         node --test suites
  tools/         stamp-sw.mjs: writes the offline file list and version into sw.js (npm run stamp)
  docs/          teardown and improvement notes
```
