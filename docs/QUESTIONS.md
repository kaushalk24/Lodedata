# Questions for the user

Everything still to be checked in Lode Data to make the replica exact, in
one list, with what to send for each. Kept up to date as answers come in;
the details behind each item are in `open-questions.md` and
`file-formats.md`.

Status: **set S answered in part (2 Oct, evening)**: the user's three
Design screenshots (BH1GHzMid and HUMB1GHzMid keyed, LK002 on LKMac862) and
the recording of NBERN1GHz's Actives window, every tab. Every figure on the
two keyed screens is now the app's, the 550 / 860 / 870 columns included;
the Actives, Parameters and Cables windows are Lode's (file-formats 3.3,
3.4b–d). **Next: set S2 below, in its order** — the first five decide what
the app computes, the rest finish the Spec Edit windows. Then set A3.
Where each answer came from: `EVIDENCE.md`.

## S2. After the BH / HUMB / LK002 screens and the NBERN recording (next)

For each: what to do in Lode, what to send, and what it settles.

S2-1. **When does Lode pick an amplifier's pads and EQs?** On your BH and
    HUMB screens 1.7's box shows Forward Pad Flag, Forward Eq CS2 (HUMB:
    CS1), Return Pad Flag, Return Eq 3 — exactly what the app's rule picks
    — but on AL004 the 88 you placed on 4.2 (28 Sep) showed 0 / SCS6 / 0 /
    0, nothing picked. *Do:* File → New with BH1GHzMid; key 71 on 1.1, a
    190-ft line with hc 2, and 11 on the line below. *Send:* the box of
    that 11 straight away; then again after 8 (Recalc); then after 5
    (Test). *Settles:* when the picking happens — the app never picks yet,
    so its 1.7 box says 000 / CS10 / 000 / 0.
S2-2. **The Test list of both screens.** *Do:* 5 (Test) on the BH and the
    HUMB network of your screenshots. *Send:* both Test lists. *Settles:*
    the app's lines: for BH none; for HUMB "Fslope / Rslope too low to
    equalize at 1.1" and four tap-window lines at 1.6 (Tap(1002) 12.57 over
    window …) — and how lines at 550 / 860 are worded.
S2-3. **HUMB's yellow `<21>` at 1.6.** Row 21 of HUMB1GHzMid's taps has no
    part at all. *Send:* the window with the cursor on 1.6's tap (its box
    showing). *Settles:* the app's reading — no part number, tap value 0,
    so the port is over its window (yellow) — against Lode's box.
S2-4. **HUMB's branch 2, behind coupler 92.** Record 92 has no part number
    and a tap leg of 99 dB at 1002 only. *Do:* double-click `92<2>` on 1.2.
    *Send:* the window on branch 2. *Settles:* what Lode does with a spec
    column that holds 0 next to one that does not: the app now takes 99 at
    1002 and fills the empty columns from it (31.59 at 102, 28.83 at 85);
    Lode probably takes the columns as they are (0). Only two pairings in
    the samples would change (AL004 opened with KERMIT's spec).
S2-5. **Same tap ID, other port counts.** HUMB1GHzMid has tap 12 only as a
    2-port. *Do:* on a line with hc 5 key 12 in tap1. *Send:* the line and
    the tap's box. *Settles:* whether Lode then takes the empty 8-port slot
    (`<12>`, as 21 at 1.6) or falls back to the 2-port (`/12/`) — the app
    falls back.
S2-6. **The Actives tab scrolled right** (NBERN1GHz or BH1GHzMid). *Send:*
    the columns after `In - F5`, rows 1–28. *Settles:* In F6, Out at F3–F6
    and whatever else the tab has; then the app's window shows them too.
S2-7. **Out/Loss.** *Do:* on a copy of a spec (Save As, a new name), set
    one active's `Out/Loss` to Loss and save. *Send:* that .atv. *Settles:*
    where Out/Loss is kept (every row of the recording reads 0 Out).
S2-8. **Plug-Ins and the Configuration Table** (WV750-2026). *Send:* the
    Plug-Ins tab (rows 1–20) and scrolled to its last row; the
    Configuration Table at rows 20/0–20/7 and 30/0–30/7. *Settles:* that
    the plug-ins are WV750's NEW LE … SWAP FMB TO FMT at rows 4–17, how many
    rows there are (31 or 32), and the Quantity columns.
S2-9. **The Taps window and the Couplers window** (any spec, BH1GHzMid
    best). *Send:* every tab of each, scrolled right where it scrolls.
    *Settles:* the app's Spec Edit → Taps and Couplers windows (they still
    show a plain list), and the bytes no reader explains yet (a byte on
    every tap row, four on every port count).
S2-10. **The Cables window's Connectors and Series/Colors tabs**
    (WVEXT862). *Send:* both. *Settles:* the last two tabs of the app's
    Cables window (it says "not seen yet").
S2-11. **Reserve Gain** (Buckhannon's BUCH1GHzMid, rows 40–45; or
    KERMIT750, rows 1–12). *Send:* the tab. *Settles:* that Ret. Mod. Part
    Number is the text at +30 (`RA-KIT-40L`); and BH's Fwd Reserve Gain
    2.00 — does reserve gain change any level or Test line?
S2-12. **LK002.ntw** with LKMac862. *Send:* the file. *Settles:* the rest
    of your third screenshot — `LK265 1.5` in the cplr column at 1.5 (a
    link to the network LK265?), the white `01` in tap2 at 1.1, branch 1
    of 73.
S2-13. (optional) **The BH network of screenshot 1 saved** (Save Network
    As… BH_TEST.ntw). *Settles:* that the app writes a network with two
    extra frequencies as Lode does.
S2-14. **Only if networks are still opened with the oldest specs:**
    Bossier's bymac862, the Actives tab; Georgetown's gefd862, the Actives,
    Cables and Couplers tabs; Bullhead's npg550, those three and the
    Parameters frequencies tab. *Settles:* the old layouts (actives 2.20 /
    3.0 / 5.0, cables and couplers 2.10), so they can be read.
S2-15. **A decision, no screenshot:** reading HUMB's empty tap row and
    unnamed coupler as Lode does also draws such taps in networks opened
    with a spec set other than their own (e.g. AL002's 32.3 with WVEXT862,
    row 0: `/24/`), which the app used to leave out. No pairing checked
    against Lode changes (AL004 + WV750, the older AL004 + WVEXT862, SN001 +
    SHINSTON, S1–S3), and nothing a save writes. *Answer:* keep, or ask
    for it to be undone.

Answered by the screenshots and the recording (2 Oct): S2 of the old list
(BH1GHzMid's F3 / F4: every figure), S6 (New Bern's `2&4 PORT` table is
EQs Bank 9), S7 (Lode heads LKMac862's columns `high low Rh Rl`), most of
S3 (the Actives window's tabs: Reserve Gain, Power Steps, Pads/EQs, EQs
Banks, Plug-Ins, Configuration Table, Bridgers, Feedermakers, Inline EQs,
Custom Cascading, Boosters), and S10 (Casc. 1–19 on the tab).

"Older AL004" below means AL004.ntw opened with the WVEXT862 spec set;
"AL004" the newer one with WV750-2026. A screenshot means the whole Lode
Data window, with the info box in the bottom-right corner showing.

## A. The older AL004 — answered

1. **Cascade position — solved.** The Actives file's Custom Cascading
   (two bytes per active) says at which cascade positions an active may
   sit. WV750's and SHINSTON's Ripple nodes may sit at 0, so the first
   amplifier after one is 1; WVEXT862's HLN 3842 NODE only at 1 and its
   NC4000 nowhere, so either node counts as 1 and every active reads one
   more (1.1 = 1, 6.1 = 2, 11.10 = 3, 25.3 = 4, 23.17 = 6: all as Lode).
   The same bytes give "LE  11/5 before/0 after at 23.17.": WVEXT862's
   "11" may sit at 1–5 and 23.17 is the 6th.
2. **The red "64" on 11.18 — answered:** no active there (the user); the
   replica draws none, as Lode now does.
3. **The 13 Test lines — solved.** An active is short when its input, less
   its forward pad and EQ, is under its In ("870 input 10.97 to LE at
   4.13."), or its Out, less its return pad and EQ, under the level needed
   there ("40 output 36.64 from LE at 25.3."); In at 550 is in the older
   Actives record at +127. All 94 of Lode's lines now come out, in its
   order, but 15.4's three (below).
4. **15.4 — Lode's own two figures differ.** Every number on branch 15 and
   in both tap boxes matches (15.4's port −4.19 on screen and in its box);
   only Lode's Test list says 23.18 / 16.98 where its screen gives 23.19 /
   16.99. Asked again in A2.
5. **Brackets — all seen.** AL004's 5.19 `100<29>`, the older 9.1
   `108<10>` and 5.19 `100<32>` as predicted. Two showed the rule wrong,
   now corrected: 16.4 is `8<17>` (a power stop on the coupler's own line
   does not end the walk back) and 9.14 `2<14>` (on 404 cable: the cable
   does not matter, only the length).

## A2. What set A raised — answered

Sent 2 Oct as `wxext862-2.zip`: AL004_SETA.ntw, its Test list, the WIFI
OMNI boxes, 25.2 and 5.9 with their cable boxes, WVEXT862's Cables tab,
S3's 1.2, and the Custom Cascading tab of WVEXT862 and WVBeck750.

A6. **AL004_SETA.ntw is the pack's file.** It differs from
   `samples/AL004-WVEXT862/AL004.ntw` only in the header's licence and user
   fields and the name it was saved under (preamble 44542). Lode's branch 5
   now starts at 1.4 and 5.1 reads 46.00, as the app has it: set A's 1a
   (HLN 3842 NODE alone on 1.1, five lines) was another copy.
A7. **The fresh Test list is the app's, all 94 lines.** 15.4 still reads
   23.18 / 16.98 / 8.06 — solved: the Test reads a port as Lode rounds it,
   a half added and the rest dropped, which takes a level under zero up a
   cent (-4.191 tests as -4.18 though the screen shows -4.19). Every line
   of the list is now the app's.
A8. **43.1 and 44.1:** Cascade Position 4 both, every figure of both boxes
   and both lines as the app has them.
A9. **Red cable numbers — solved.** The cable number is the series (its
   hundreds) and the cable ID; the cable file holds, for each cable, ten
   series slots with a colour and a name (Spec Edit → Cables →
   Series/Colors), and Lode draws the number in that colour. WVEXT862:
   cables 0–19 red on series 0, 2, 3, 5, green on 1 and 4; cables 20–39
   red on 4 only — so 505 and 515 red, 438 red, 404–415 green. WV750 and
   KERMIT leave every slot at the default bright green (515 not red);
   SHINSTON sets cables 0–39 a darker green on series 0–5 (SN001's 15.29
   "10", drawn so in SHINSTON2 1b). The line's box names the series after
   the cable from column 15 ("EX P3 625 U    Dual New Build"). The user:
   5xx are risers (aerial–underground, 20 or 25 ft), 1xx double runs, 4xx
   here not a 4th run, 2xx rarely a riser.
A10. **S3's 1.2 reads `100<2>`**, as the corrected rule draws it. Lode
    draws that coupler red (A14); the user's S3 has also been edited since
    the pack's copy (taps 14, 47.71 at 1.2).
A11. Not answered yet — asked again in A3.
A12. **Custom Cascading — solved.** Every row of both tabs reads from the
    actives' u16: bit 0 Cust. Casc. (Yes/No), bit 1 Exclude, bit k + 1
    Casc. k Valid (k 1–14; the tab shows 19 columns, 15–19 Invalid on every
    row). Ripple and Ripple No Power are Yes, Exclude, Casc. 1; WVEXT862's
    HLN 3842 NODE Yes, Include, Casc. 1; NC4000 and the WIFI OMNI No.
    Cascade Position counts the actives that are not excluded (A13 checks
    the middle of a cascade).

## A3. What set A2 raised (after set S)

A13. **Exclude in the middle of a cascade.** On a copy of AL004 (File →
    Save Network As… AL004_X.ntw, with WV750-2026), put a Ripple (70) on
    4.20, a line with no active between bridgers 4.13 and 4.24. *Send:*
    the amp boxes of 4.20 and 4.24. *Settles:* whether an excluded active
    counts in the cascade. The app reads 4.24 as 2 (not counted) and the
    Ripple 0; if Lode says 3, it counts.
A14. **S3's red coupler.** *Send:* S3 as it is now (File → Save Network
    As… S3_A2.ntw) and the whole window with the cursor on 1.2's coupler,
    info box showing. *Settles:* why Lode draws `100<2>` red (the app draws
    it green).
A11. **Crossover spacing** (again). Lode prints "Crossover of    3.85" (the
    figure seven wide — your 2 Oct list again); the app prints "Crossover
    of  3.85". *Answer:* yes or no to changing it (it changes AL004's Test
    list text).

## B. Couplers and branches

6. **Two-branch coupler.** On a splitter feeding two branches
   (AL004 4.14, `3-<11><12>`): what do `. ←` and `. →` do, and does a
   double-click on the second bracket enter the second branch?
   *Send:* a note of what happens on 4.14.
   Also: after the mouse wheel (or `. ←`) brings you back from a branch,
   is the cursor on the coupler cell or on ftg (the app: ftg)? And does
   View > Show Tips stay off after Lode is closed and reopened (the app:
   tips come back on reload)?
7. **`{n}` and `(n)`.** The manual lists `{n}` (backfeed) and `(n)` (no
   footage), but Lode draws backward-running and no-footage branches
   `<n>`. *Send:* any screenshot where Lode draws `{n}` or `(n)`, if you
   ever see one.
8. **5xx cable — answered by set A:** the cable does not matter, only the
   span's length (the older AL004's 9.14 is `2<14>` on 404, mileage).

## C. Branches fed from a tap's port (the older AL004's 43 and 44)

9. **Several taps on one line.** When a line has more than one tap, which
   tap feeds the branch, and where does the "Branch:" line sit in that
   tap's box? *Send:* a screenshot of such a line and its tap box.
10. **Clearing that tap.** What does `0` on a tap that feeds a branch do
    (the replica keeps the branch, fed by nothing)? *Send:* a note or a
    screenshot before/after, on a copy of the file.

## D. The expanded display (`/`)

11. (a) Does a 0-ft first line (AL004 22.1) show the cyan block for being
    first, or for being 0 ft on from a coupler? *Send:* the expanded
    display at any of AL004 5.25, 9.2, 10.4, 14.5, 20.18, 25.2, 29.3,
    29.7, 36.2, 37.2.
12. (b) What is the third count in the block's `2-2-0` triples (always 0
    so far)? *Send:* the expanded display of a line below one of WV750's
    FM901e-B, FM901e-T, FM902B, FM902T, FML332 or FML1G7J actives.
13. (c) How Lode tells a bridger from a line extender. *Send:* the Actives
    Specs window's Bridgers tab and Custom Cascading tab.
14. (d) The housing marker where the location's first line carries
    nothing: AL004 5.29 + 5.30. *Send:* the expanded display at 5.29.
15. (e) What the cyan `(1)` under ftg on a tap's line counts. *Send:* the
    expanded display of a line with two or more taps.
16. The small three-option dialog seen in your early videos (possibly
    NETWORK MODIFIED: 3 Restore, 7 Save, 9 Switch). *Send:* a screenshot
    if it appears again.

## E. What Lode writes (saving .ntw files)

17. **TSG, Map, Loc and address.** Where the file keeps them (the replica
    reports them as "not written"). *Send:* two saves of the same network
    from Lode — one before, one after setting a TSG, Map, Loc and address
    on one line (say which line and the values).
18. **A new power supply.** *Send:* two saves from Lode — before and after
    placing one power supply on one line (say which line, which supply).
19. **House lists of new lines.** Which new lines get their house list
    filled in. *Send:* two saves — before and after adding a line with 2
    homes and one with 0.
20. **Counters not decoded** (preamble 23481/23483 and the three pairs at
    36121). Answered by the same kind of before/after saves as 17–19; no
    separate send needed.
21. **Power stops on the older files.** AL002–AL005 set the power stop
    field on many more lines than AL004. *Send:* the Power screen of
    AL002 (any branch) with its spec set, showing where Lode draws `=`.
22. **AL004_NOTES** (optional — SN001 already proved Notes). Open
    AL004_NOTES.ntw with WV750-2026 and check `..+` on 2.1 and 4.13.

## F. Files

23. **WVBeck750 spec set** (.par .atv .tap .cpr .cbl). 34 of the tests
    need it and skip without it.
24. **The spec sets AL002, AL003 and AL005 were designed with**, so they
    can be checked like AL004.
25. **The "ntw map AL004" file** mentioned early on (never arrived).

## G. The repository

26. Earlier commits of `docs/file-formats.md` and
    `tools/lodedata/header.py` quote licence and user ids from the files'
    headers. The current files no longer do (replaced before the server
    zip). Remove them from the repository's history as well? That rewrites
    the branch's history.
