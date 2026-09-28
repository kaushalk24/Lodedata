# Overload

A free, offline-first workout tracker modelled on Setgraph's fast "exercise notepad" logging, with the paid parts
rebuilt to run on your phone. No account, no subscription, no server.

- **Sets**: workout folders, My Exercises with a 130-exercise library, templates, and an offline plan designer.
- **Exercise**: history grouped by day with *Compared to previous*, a chart, 1RM with a percentage table, and records.
- **Set entry**: custom keypad prefilled from your last set, a "beat last time" target, a live PR badge, labels,
  a plate calculator, bodyweight sets, kg/lb, backdating and a rest timer.
- **Sessions**: timed activities such as strength training, tennis or a run.
- **Body**: recovery map, weekly sets per muscle, bodyweight log.
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

1. Host the `overload/` folder on any static host. GitHub Pages is free: *Settings → Pages → Deploy from a branch*,
   then open `https://<you>.github.io/<repo>/overload/`. Netlify Drop and Cloudflare Pages also work.
2. **iPhone**: open the link in Safari → Share → **Add to Home Screen**. It then runs full screen and offline.
3. **Android**: open it in Chrome → menu → **Install app**.

Data lives in the browser's storage on that phone (IndexedDB). Save a backup now and then from
*Settings → Import & Export*.

## Bring your history

*Settings → Import & Export → Import CSV from another app* reads CSV exports from Setgraph, Strong, Hevy or a
spreadsheet. Columns are detected (exercise, date, time, reps, weight, note, set type) and you can adjust them before
importing. Importing the same file twice doesn't create duplicates.

## Tests

```sh
cd overload && npm test      # or `node --test` from the repo root
```

The tests cover the analytics against the exact numbers in the recording, plus the planner, CSV import/export,
date parsing and muscle guessing.

## Layout

```
overload/
  index.html, manifest.webmanifest, sw.js   app shell, install metadata, offline cache
  css/app.css                               tokens (dark + light) and components
  js/
    util.js      escaping, units, dates, CSV            stats.js    records, PRs, 1RM, plates, progression, recovery, streaks
    library.js   exercises, muscles, templates          planner.js  offline plan designer
    store.js     state, IndexedDB, mutations            dataio.js   CSV import/export, demo data
    ui.js        navigation, sheets, dialogs, toasts    timer.js    rest timer
    chart.js     SVG chart                              bodymap.js  SVG muscle map
    screens/     home, exercises, exercise, setentry, sessions, body, today, settings
  tests/         node --test suites
  docs/          teardown and improvement notes
```
