# Questions for the user

Every question still open, first to last, in priority order (3 Oct). Each
says what to do in Lode Data, what to send, what it settles, and what the
app does now. A screenshot means the whole Lode window, info box showing.
"BH" = BH1GHzMid, "HUMB" = HUMB1GHzMid (the 7-29-2025 sets), "BH network"
and "HUMB network" = the two networks of the 2 Oct screenshots (1.1 amp
71; 1.2-1.4 coupler 99 or 92 to branches 2-4; 1.5 190 ft hc 2 tap 26; 1.6
189 ft hc 5 tap 21; 1.7 amp 11) — key them again that way if you did not
save them. Answers so far and where they came from: `EVIDENCE.md`; the
answered sets are at the end of this file.

## Priority 1 — what the app computes (levels, colours, Test lines)

1. **When does Lode pick an amplifier's pads and EQs?** *Do:* spec BH, File
   → New; 1.1 amp 71; Insert a line 1.2, ftg 190, hc 2; Insert a line 1.3,
   amp 11. Put the cursor on 1.3's amp cell and take a screenshot before
   pressing anything else; press 8 (Recalc), screenshot; press 5 (Test),
   Esc, screenshot. *Settles:* whether Lode picks them when the amp is
   keyed, on Recalc or on Test. *App now:* never picks for a keyed amp —
   the box reads Forward Pad 000, Forward Eq CS10, Return Pad 000, Return
   Eq 0, where your BH screenshot reads Flag / CS2 / Flag / 3. (On AL004's
   4.2, 28 Sep, Lode showed 0 / SCS6 / 0 / 0: nothing picked.)
2. **The Test lists of the BH and HUMB networks.** *Do:* open (or key)
   each, press 5 (Test). *Send:* the Test Results window, every line
   (scroll if needed). *Settles:* the slope and tap-window checks on the
   two regions' specs.
   *App now:* BH — no lines. HUMB — six: "Fslope too low to equalize at
   1.1.", "Rslope too low to equalize at 1.1.", "Tap(1002) 12.57 over window
   at 1.6.", "Tap(102)  9.90 over window at 1.6.", "Tap(85) 12.12 below
   window at 1.6.", "Tap(5) 14.09 below window at 1.6.".
3. **HUMB 1.6's yellow `<21>`.** *Do:* HUMB network, cursor on 1.6's tap1
   cell. *Send:* screenshot with its box. *Settles:* how Lode reads a tap
   row that has an ID (21) but no part for any port count. *App now:* part
   number blank, tap value 0 and insertion 0, so the port reads the line
   (39.57 at 1002), 12.57 over its 10 dB window: yellow.
4. **HUMB's branch 2, behind coupler 92.** *Do:* HUMB network, double-click
   `92<2>` on 1.2. *Send:* screenshot of branch 2. *Settles:* whether Lode
   takes a 0 in a spec column as 0 dB. Coupler 92's tap leg is 99 at 1002
   and 0 at every other column. *App now:* 2.1 reads -48.00 5.41 39.83 17.99
   | 44.50 49.00 (it fills the 0 columns from the 99). If Lode reads -48.00
   37.00 11.00 11.00 | 44.50 49.00, the app takes each column as it is —
   that changes only AL004 opened with KERMIT's spec among the samples.
5. **A tap ID keyed with a port count its row does not have.** HUMB has tap
   12 only as a 2-port. *Do:* HUMB network, Insert a line under 1.7, ftg
   100, hc 5, key 12 in tap1. *Send:* screenshot with the tap's box.
   *Settles:* `<12>` (the empty 8-port slot, as 21 at 1.6) or `/12/` (the
   2-port). *App now:* `/12/`.
6. **An excluded active in the middle of a cascade.** *Do:* AL004 with
   WV750-2026, File → Save Network As… AL004_X.ntw; 4.20 has no active
   (it lies between the bridgers on 4.13 and 4.24): key 70 (Ripple) in its
   amp cell. *Send:* screenshots with the cursor on 4.20's amp and on
   4.24's amp (boxes showing). *Settles:* whether an active marked Exclude
   in Custom Cascading counts in Cascade Position. *App now:* Cascade
   Position 0 at 4.20 and 2 at 4.24; if Lode says 3 at 4.24, it counts.
7. **S3's red coupler.** *Do:* open your S3.ntw as it is now, File → Save
   Network As… S3_A2.ntw; cursor on 1.2's coupler. *Send:* S3_A2.ntw and the
   screenshot. *Settles:* why Lode draws `100<2>` red. *App now:* green.
8. **Crossover spacing (yes / no).** In the Test list Lode writes the
   crossover figure seven characters wide, "Crossover of    3.85 at 3.5."
   (your 2 Oct list of AL004_SETA); the app writes it five wide,
   "Crossover of  3.85 at 3.5.". *Answer:* yes = write it as Lode does
   (only the spacing of the Crossover lines changes, on every network);
   no = leave it.
9. **Empty tap slots in networks opened with another spec set (keep /
   undo).** Since 2 Oct a tap ID whose row has no part (HUMB's 21) is drawn
   and passes the levels at 0 dB, as Lode draws it, and a stored pad on a
   bank's Flag row shows `FLAG`. Side effect: 32 of the 70 sample pairings
   changed — all networks opened with a spec set other than their own,
   which now draw such taps where the app left them out (e.g. AL002's 32.3
   with WVEXT862: `/24/`). No pairing checked against Lode changed, and no
   saved byte. *Answer:* keep or undo.
10. **Reserve gain.** *Do:* spec BH, Spec Edit → Actives → Reserve Gain,
    rows 1–28. *Send:* screenshot. Then: does Reserve Gain change any level
    or Test line in your work (yes / no / don't know)? *Settles:* the app
    reads Fwd Reserve Gain 2.00 on BH's FM332 rows and uses it nowhere.

## Priority 2 — spec file fields not read yet

11. **The Actives tab, scrolled right.** *Do:* spec BH, Spec Edit → Actives
    → Actives tab; drag the bottom scroll bar fully right. *Send:*
    screenshot, rows 1–28. *Settles:* every column after "In - F5" (In F6,
    Out at 550 / 860, …); the app's window shows only up to In - F5.
12. **Out/Loss.** *Do:* Spec Edit → Actives on any spec; File → Save As a
    new name (e.g. TEST_OL); on row 1 set the Out/Loss next to "Out - 1002"
    to Loss; File → Save. *Send:* TEST_OL.atv. *Settles:* where Out/Loss is
    kept (every row of your recording reads 0 Out; the app shows 0 Out).
13. **Plug-Ins and the Configuration Table.** *Do:* spec WV750-2026, Spec
    Edit → Actives. *Send:* the Plug-Ins tab at the top (rows 1–20) and
    scrolled to its last row; the Configuration Table scrolled to rows
    20/0–20/7 and 30/0–30/7. *Settles:* how many plug-in rows there are
    (31 or 32), that rows 4–17 are SWAP BR TO LE … SWAP FMB TO FMT, and
    the Quantity columns. *App now:* 68N–68B take Plugin 1 = 8 9 10 11 16
    (NEW FMB … SWAP FMT TO FMB), quantities 0.
14. **The Taps window.** *Do:* spec BH, Spec Edit → Taps. *Send:* every tab,
    scrolled right where it scrolls. *Settles:* the app's Taps window (a
    plain list now) and the tap bytes no reader explains.
15. **The Couplers window.** *Do:* spec HUMB, Spec Edit → Couplers. *Send:*
    every tab (rows 1–30 showing, including 92). *Settles:* the app's
    Couplers window (a plain list now).
16. **The Cables window's other tabs.** *Do:* spec WVEXT862, Spec Edit →
    Cables. *Send:* the Connectors tab and the Series/Colors tab. *Settles:*
    those two tabs (the app says "not seen yet").
17. **Ret. Mod. Part Number.** *Do:* spec BUCH1GHzMid (Buckhannon), Spec
    Edit → Actives → Reserve Gain, rows 35–50. *Send:* screenshot.
    *Settles:* that row 42 reads RA-KIT-40L (the text the app reads there).
18. **Bridgers, Feedermakers, Boosters (yes / no).** Every spec you sent
    has these tabs empty. *Answer:* do you ever fill them in? If yes, send
    one spec where they are filled, with screenshots of those tabs.
19. **The oldest spec formats (yes / no).** Do you still open networks with
    Bossier's bymac862, Georgetown's gefd862 / jarr625, Bullhead's npg550 /
    npg750 / npg860 or Beckley's steph870? If yes: their Spec Edit →
    Actives, Cables and Couplers tabs and the Parameters' Frequencies tab
    (one spec is enough to start). *App now:* cannot read them.

## Priority 3 — networks and files to send

20. **LK002.ntw** (with LKMac862). *Send:* the file. *Settles:* your third
    screenshot: `LK265 1.5` in the cplr column at 1.5, the white `01` in
    tap2 at 1.1, the gutter marks, branch 1 of 73.
21. **The BH network saved.** *Do:* File → Save Network As… BH_TEST.ntw.
    *Send:* the file. *Settles:* that the app writes a network with two
    extra frequencies byte for byte as Lode does.
22. **WVBeck750 (yes / no).** You sent it on 29 Sep. May it go into the
    test samples? 34 tests use it.
23. **The spec sets AL002, AL003 and AL005 were designed with.** *Send:*
    them if you have them (AL002 and AL003 name "WVEXT862", AL005
    "Beckley750"; the WVEXT862 you sent may be a later one). *Settles:*
    checking those networks as AL004 is checked.
24. **The "ntw map AL004" file** mentioned early on — still wanted?

## Priority 4 — couplers, branches and taps on the Design screen

25. **Two-branch coupler.** *Do:* AL004 + WV750, line 4.14 (`3-<11><12>`):
    press `.` then `←`, and `.` then `→`; double-click the second bracket
    `<12>`. *Send:* a note of where each takes the cursor. Also: after the
    mouse wheel brings you back from a branch, is the cursor on the coupler
    cell or on ftg (the app: ftg)? After closing and reopening Lode, is
    View → Show Tips still off if you turned it off (the app: back on)?
26. **`{n}` and `(n)`.** The manual lists `{n}` (backfeed) and `(n)` (no
    footage); every no-footage and backward branch seen is drawn `<n>`.
    *Send:* any screenshot where Lode draws `{n}` or `(n)`, if you ever
    see one.
27. **Several taps on one line feeding a branch.** *Send:* a screenshot of
    a line with two or more taps where one feeds a branch, cursor on that
    tap (box showing). *Settles:* which tap feeds it and where the
    "Branch:" line sits in its box.
28. **0 on a tap that feeds a branch.** *Do:* on a copy (Save As), put the
    cursor on such a tap and key 0. *Send:* before and after screenshots.
    *App now:* the branch stays, fed by nothing (starts at 0.00).

## Priority 5 — the expanded display (`/`)

29. **The block on a 0-ft first line.** *Do:* AL004 + WV750, `/` on, at any
    of 5.25, 9.2, 10.4, 14.5, 20.18, 25.2, 29.3, 29.7, 36.2, 37.2. *Send:*
    screenshots. *Settles:* whether the cyan block is drawn for a branch's
    first line or for a 0-ft line after a coupler.
30. **The third count in `2-2-0`.** *Do:* `/` on a line below one of WV750's
    FM901e-B, FM901e-T, FM902B, FM902T, FML332 or FML1G7J. *Send:*
    screenshot. *Settles:* what the third number counts (0 everywhere so
    far).
31. **The housing marker at AL004 5.29.** *Do:* `/` at 5.29 (5.29 and 5.30
    are one location, the first line carrying nothing). *Send:* screenshot.
32. **The cyan `(1)` under ftg.** *Do:* `/` on a line with two or more
    taps. *Send:* screenshot. *Settles:* what it counts.
33. **The three-option dialog** from your early videos (possibly "NETWORK
    MODIFIED": 3 Restore, 7 Save, 9 Switch). *Send:* a screenshot if it
    appears again, and what brought it up.

## Priority 6 — what Lode writes when saving

34. **TSG, Map, Loc and address.** *Do:* on a copy of AL004, Save As
    TSG_A.ntw; on 4.24 set TSG 2, Map 7, Loc 12 and an address; Save As
    TSG_B.ntw. *Send:* both files and the values used. *Settles:* where
    the file keeps them (the app does not write them yet).
35. **A new power supply.** *Do:* on a copy, Save As PS_A.ntw; place one
    supply on one line; Save As PS_B.ntw. *Send:* both, and the line and
    supply. *Settles:* the supply's record.
36. **House lists of new lines.** *Do:* on a copy, Save As H_A.ntw; add a
    line with 2 homes and one with 0; Save As H_B.ntw. *Send:* both.
    *Settles:* which lines get a house list (and, with 34–35, the counters
    at 23481 / 23483 / 36121).
37. **Power stops on the older files.** *Do:* AL002 with its spec set,
    Power screen, any branch. *Send:* screenshot. *Settles:* where Lode
    draws `=` (AL002–AL005 set the power-stop field on many lines).
38. **AL004_NOTES.ntw** (optional). Open it with WV750-2026; check `..+` on
    2.1 and 4.13 shows the notes the app wrote.

## Priority 7 — later work (when we get there)

39. **The design commands.** A short recording of each screen-menu command
    on a copy of AL004: 6 WillWrk, 7 AutoCpl, 8 Recalc, 9 Toggle, .7 SetMDU,
    .8 RotTap and the others — what each changes.
40. **Connecting networks.** A recording of connecting two networks (PCD
    connect, two networks sharing a power supply).
41. **Spec Edit → Pricing, Performance and Control.** Screenshots of each
    window's tabs, and the files (.prc, .per) if you use them.
42. **The repository's history (yes / no).** Old commits of
    `docs/file-formats.md` and `tools/lodedata/header.py` quote licence
    and user ids from file headers (removed from the current files).
    Rewrite the branch's history to remove them?

---

## Answered (2 Oct, evening): BH / HUMB / LK002 and the NBERN recording

Every figure on the keyed BH and HUMB screens is the app's (550 / 860 / 870
columns included); Lode heads LKMac862's columns `high low Rh Rl`; New
Bern's `2&4 PORT` table is EQs Bank 9; the Actives window's tabs (Reserve
Gain, Power Steps, Pads/EQs, EQs Banks, Plug-Ins, Configuration Table,
Bridgers, Feedermakers, Inline EQs, Custom Cascading, Boosters) and Casc.
1–19. The coupler "code" (402, 408, 612 …) is simply the ID the user types
(WV750's RLS12-2 is 402): nothing to decode.

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

