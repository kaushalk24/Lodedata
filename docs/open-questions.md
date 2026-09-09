# What is still needed

Updated after recovering much of the vendor manual through web search — see
`lode-data-manual-notes.md`. Several earlier questions are now answered; what
remains is listed below.

## Resolved since the first pass

* **Cable attenuation model.** The four loss columns are the forward High,
  forward Low, return Rh and return Rl frequencies, in dB per 100 ft, at the
  frequencies set in the Parameters file. Confirmed by the manual and by ratio
  analysis over 62 cables in two spec sets. Applied to the importer.
* **Loop resistance.** Ohms per 1000 ft (or per 1000 m in metric), and `99` is
  the sentinel for "never power this". Applied.
* **Cable IDs.** 0–99, even = aerial, odd = underground. Zero exceptions across
  both spec sets. Applied.
* **Coupler losses.** Two loss blocks per record, same layout as cables.
  Applied.
* **Why `.ntw` files hold no text.** The manual confirms spec files define every
  piece of equipment; the design file only references them.

## 1. Screenshots — the remaining documentation gap

Web search returns text, not images, and a good part of this manual is pictures
of the screen. I still have not seen the application. If you want the interface
to match, this is what to send — browser **Save page as → Web page, complete**,
zipped, keeps the images:

* Design Mode and Entry Mode screens (the column layout and how a row reads)
* the Network Initialization window
* the cable, tap, coupler and active spec editors
* Powering Mode
* the Parameters tap-selection tab

## 2. Ground truth for the remaining numbers

Still guessing at these, and one screenshot each settles them:

1. **Tap spec editor for `MMT2830`** — I can read the part numbers per port
   count but not yet the tap loss, insertion loss and self-term values inside
   the record's sub-blocks.
2. **Active spec editor for `BLE-7-750PSS`** — the numeric block decodes to
   19 / 15 / 21 / 49 / 38 / 43 dB plus a response table of pairs
   `(38, 0.69) (45, 0.62) (52, 0.58) …`. The manual gives me module input,
   noise figure and output tilt as the fields to expect, but not which is which.
3. **Which coupler leg is "Thru"** — the numbers say leg A is the tap leg; one
   look at the editor confirms or flips it.

## 3. A data question about your spec files, not the format

Both sample spec sets carry attenuation roughly **40% above** the published
catalogue figures for the cables they name. `EX .500P3` is entered as 2.16
dB/100 ft at the forward high frequency; pristine .500 P3 is about 1.53 at
860 MHz. The ratios between frequencies and between cable sizes are all correct,
so this is not a decoding error — every cable is scaled up consistently.

Is that deliberate (an aged-plant or "existing" allowance, since the parts are
named `EX …` and `… EXT`), or are those files entered against a much higher
forward frequency than the 860 MHz the ratios imply? It changes every level the
app computes from an imported spec set.

## 4. The `.ntw` record layout — the one real blocker left

The obfuscation is solved and the payload is readable, but the record layout is
not mapped, and design files contain no text to bootstrap from.

Fastest unlock, by a distance: **build a deliberately tiny design and send me
the file plus its report.** A power supply, one amplifier, one span of `.500P3`
at a known footage, one tap, a terminator. Send the `.ntw`, its spec set, and a
printed or exported design report. With known content I can identify every table
quickly; with only large real designs it stays guesswork.

Nearly as good and much cheaper: export any report from one of the `AL00x.ntw`
files you already sent. The manual says reports can be written to `.XLS`
("simply type the name of the Excel file followed by .XLS"), so a Single Network
BOM or an Active report as a spreadsheet would give me rows to match against the
binary.

Also useful: two `.ntw` files that differ by exactly one known edit — save, add
one 26 dB tap, save again. Diffing those points straight at the tap table.

## 5. Product direction, now that the manual has shown its hand

The real program's input model is a **keyboard-driven span sheet**, not forms:
type `1 0 7 . 2 . 0 ⏎` for 107 feet, 2 houses, cable 0, where `.` moves to the
next column. Columns are `ftg | hc | cab | lv`, and the same rows gain computed
columns in Design mode and voltage/current in Powering mode.

That is much faster than the form-based inspector currently in the app, and it
is what your designers will expect. Worth building — but it is a real piece of
work, so say the word before I do it.
