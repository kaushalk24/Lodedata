# Questions for the user

Updated 4 Oct, evening. Only what the app cannot settle without Lode Data
is asked; everything else from your answers of 4 Oct (`6.zip`) is solved and
listed under "Answered". Each question says why it is needed, what to do in
Lode step by step, what to send, what it settles and what the app does
meanwhile. "Screenshot" means the whole Lode window with the info box
showing. Work on copies: never save over AL004.ntw itself. Where every
answer came from: `EVIDENCE.md`.

## Open — needed to finish the app

**N1b. Why Lode did not pick 88's pads (4.2).**
*Why:* every active keyed so far had its pads and EQs picked at once, but
WV750's 88 (FML1G7J ALC LE) on AL004 4.2 kept Forward Pad 0, Forward Eq
SCS6, Return Pad 0, Return Eq 0 — still after 4.1's ftg 476 → 477 (N1a,
N1b). The app picks 20 / SCS2 / 19 / 2 there, so on this one the app and
Lode differ. Three things could cause it; one test each tells them apart.
*Do* (AL004 with WV750-2026; do not save — close with No after each):
1. Open AL004. Cursor on 4.2's **amp** cell, press `0`, key `63`, Enter
   (63 = FM901e-B, which uses the same pad and EQ banks as 88).
   Screenshot with the cursor on 4.2's amp cell.
2. Open AL004 again. Cursor on 4.2's amp cell, `0`, key `32`, Enter
   (32 = LE 750MHz ALC, another ALC line extender, on the line extenders'
   bank). Screenshot the same way.
3. Open AL004 again. Cursor on **4.11**'s amp cell, `0`, key `88`, Enter.
   Screenshot the same way.
*Send:* the three screenshots (each box shows Forward Pad, Forward Eq,
Return Pad, Return Eq).
*Settles:* 1 picked → the banks are not the cause; 2 not picked → Lode does
not pick ALC actives; 3 picked → it was 4.2's input level.
*App now:* picks 88 like any other active.

**34. TSG, Map, Loc and address — where the file keeps them.**
*Why:* the app lets you key all four but cannot save them yet: nothing
says where they sit in the `.ntw`. Two saves of the same network, before
and after, show exactly which bytes they use.
*Do:*
1. Open AL004 with WV750-2026. File → Save Network As… `TSG_A.ntw`.
2. Design mode. Put the cursor on 4.24's **TSG** cell (the column between
   amp and tap1). Press `0`, key `2`, Enter. If the status bar or a box
   asks anything, screenshot it.
3. Put the cursor on 4.24's **ftg** cell. Its box ends
   `<double-click or [.][ENTER] to edit address>`: press `.` then Enter,
   type `123 TEST ST`. Screenshot the window before you press OK, then OK.
4. Mode → **Entry**. Go to 4.24 (branch 4, node 24). Key `7` in its **Map**
   column and `12` in its **Loc** column (the manual: Entry has Branch,
   Node, ftg, hc, cab, lv, TSG, Map, Loc). Screenshot the Entry screen
   showing 4.24.
5. Mode → Design. File → Save Network As… `TSG_B.ntw`.
*Send:* `TSG_A.ntw`, `TSG_B.ntw` and the screenshots. If any step goes
differently (no TSG column, no Map/Loc in Entry, a different key), say what
you did instead.
*Settles:* where TSG, the address, Map and Loc are written.
*App now:* keeps them while the network is open; a save drops them.

**35b. Keying a power supply in Power mode.**
*Why:* PS_B gave the supply's record exactly (the app now writes it as Lode
does), but not the keys: 35a shows `PW04` in 46.1's supply cell, 35b `C`
with `\04 0%`. The app has to accept the same keys in the same order.
*Do:* open `PS_A.ntw` with WV750-2026 (the copy without the new supply).
Key the power inserter on 2.1 as you did (coupler `1`). Then Mode →
Powering, go to 46.1, and before every key you press take a screenshot
(the status bar at the bottom shows Lode's prompt), up to the moment the
supply cell reads `C`. Do not save.
*Send:* the screenshots in order, and the keys you pressed between them
(e.g. "0, then 4, Enter, then C, Enter").
*Settles:* what `PW04` is (type 4's default name?) and how the type and
the name are entered.
*App now:* a number typed in Power's supply cell sets the supply's volts;
it cannot name the supply or pick its type from the keyboard yet.

**33b. Restore and Switch in the Network Modified box.**
*Why:* the box (33.png) is in the app; `[7] Save` saves, but what
`[3] Restore` and `[9] Switch` do is not known, so the app only says
"not implemented yet" for them.
*Do:* open a copy of AL004 (Save As `NM_TEST.ntw` first). Change 4.1's ftg
476 → 477. Press Num Lock, click `[3] Restore`: screenshot what appears and
then branch 4. Change 4.1's ftg again, Num Lock, click `[9] Switch`:
screenshot what appears.
*Send:* the screenshots.
*Settles:* what each does.

**43. The cursor Lode saves.**
*Why:* Lode writes the cursor's branch and line into the file on every
save (AL005: 12.25, H_B: 2.2, PS_B: 46.1, BH_KEYED: 1.3). The app keeps
whatever the opened file held, so its saves differ from Lode's in those 8
bytes only.
*Do:* open `AL005.ntw` with Beckley750: screenshot right after it opens,
before touching anything. Then open `H_B.ntw`: the same.
*Send:* the two screenshots.
*Settles:* whether Lode reopens a network at the line it was saved on.
*And a yes / no:* may the app write its own cursor position on save, as
Lode does? It changes those 8 bytes in a saved file whenever the cursor is
not on 1.1 (nothing else).

**N11b. A network on an old spec set (NPG550).**
*Why:* the oldest Actives formats (2.20, 3.0, 5.0: NPG550, bymac862,
gefd862, jarr625, npg750, npg860, steph870) are read from your recording
(19a) only; a network checks the reading. You have no network on any of
them, so key a small one.
*Do:* File → New, then load NPG550 for all the spec files (Set All
Files). Key:
1. 1.1: amp `61` (or the first amplifier ID NPG550's Actives tab lists).
2. 1.2: ftg `190`, hc `2`, a tap `0 2 . 4` (or the nearest 2-port tap it
   offers).
3. 1.3: ftg `150`, amp: the first line extender ID it lists.
4. 1.4: ftg `100`, hc `3`, a 4-port tap.
File → Save Network As… `NPG_KEYED.ntw`.
*Send:* `NPG_KEYED.ntw`; a screenshot of branch 1 with `/` (expanded) on;
one with the cursor on each amp cell (1.1 and 1.3, their boxes showing);
the Test list (`5`).
*Settles:* the oldest actives' levels, pads and EQs, checked figure for
figure.
*App now:* cannot read those spec sets' actives yet; they are decoded
next, from 19a, and this network checks the result.

**44. (Optional) The `↕` in Power mode.**
*Why:* in 37.png (AL002 branch 4, Power) 4.4's amp cell reads `61↕`; the
app draws `61`. Nothing explains the mark.
*Do:* AL002 with WVEXT862, Mode → Powering, branch 4. Put the cursor on
4.4's amp cell: screenshot (its box showing). If Help or the manual names
the mark, say where.
*Settles:* what the mark means and when Lode draws it.

## Priority 7 — later work, in this order (when we get there)

39. **The design commands.** *Why:* the next big piece is the design engine
    — what each screen-menu command changes. *Do:* on a copy of AL004
    (Save As `CMD_BASE.ntw`), for each command below: open `CMD_BASE.ntw`,
    put the cursor where it says, take a screenshot, press the keys, take a
    screenshot of every prompt or box, answer with the default (Enter), take
    a screenshot of the result, then File → Save Network As… `CMD_<name>.ntw`
    (e.g. `CMD_AutoCpl.ntw`). The files show exactly what changed.
    * `7 AutoCpl` — cursor on 4.9's cplr cell (no coupler there).
    * `6 WillWrk` — cursor on 4.24's amp cell.
    * `.6 XWillWk` — cursor on 4.24's amp cell, after WillWrk.
    * `9 Toggle` — cursor on 4.27's tap1 cell (`[17]`).
    * `.8 RotTap` — cursor on 4.27's tap1 cell.
    * `.7 SetMDU` — cursor on 4.27's hc cell.
    * `2 Forward`, `4 Fwd2A`, `.4 XFd2A` — cursor on 4.24's amp cell.
    * `.2 BkFeed`, `.3 UnBkFd`, `..2 FwdFd`, `..3 UnFFd` — cursor on 4.4's
      cplr cell (`12{6}`).
    * `.0 Break`, `.1 Join` — cursor on 4.10's ftg cell.
    * `.5 MoveCpl` — cursor on 4.17's cplr cell (`1(18)`).
    * `..7 CAwBF`, `..8 XCAmp`, `..9 LckDStr`, `..4 BrLabel`, `..0 SpcVw`,
      `..1 Xspec` — cursor on 4.24's amp cell.
    *Send:* every screenshot and `CMD_*.ntw`, named by command.
    *Settles:* each command's effect, built one by one.
40. **Connecting networks.** *Why:* H043A_MID and H043B_MID share a supply
    through a PCD; how Lode joins them is not seen. *Do:* open H043B_MID with
    BH1GHzMid; put the cursor on 1.1's PCD cell (`H043A_MID 1.1`); try
    Misc → Connect (and, if it asks, choose H043A_MID); screenshot every box
    in order; Power mode on branch 1 after it. A short screen recording is
    best (under 2 minutes). Do not save over the originals: Save As
    `H043B_CONN.ntw` at the end.
    *Send:* the recording or screenshots and `H043B_CONN.ntw`.
    *Settles:* the PCD connect and the shared supply's volts.
41. **Spec Edit → Pricing, Performance and Control.** *Do:* with WV750-2026
    loaded, open each of the three windows and click through every tab,
    one screenshot per tab (or one recording). *Send:* the screenshots, and
    the `.prc` / `.per` files if WV750-2026 has them (same folder as its
    `.par`). *Settles:* the three windows the app does not draw yet.
42. **The repository's history (yes / no).** Old commits of
    `docs/file-formats.md` and `tools/lodedata/header.py` (before 26 Sep)
    quote licence and user ids from file headers; the current files do not.
    Rewriting the branch's history removes them from every old commit, but
    anyone with an old clone must clone again. *Answer:* yes (rewrite) or no
    (leave the history as it is).

## Answered 4 Oct, evening (`6.zip`)

* **22** — WVBeck750 is in the samples; its 34 tests run (none skipped).
* **28** — `0` `0` on the older AL004's 11.16 `117+` asks "Deleting Branch —
  Deleting this branch will delete all downstream design. Continue?"; Yes
  takes the tap off and branches 43 and 44 stay, fed by nothing (28A/28b,
  33). The app now asks the same and does the same.
* **33** — Num Lock after an edit opens "Network Modified": `[3] Restore`,
  `[7] Save`, `[9] Switch`, Close. Now in the app (33b asks the rest).
  Every level on 33 and 11.11's box match.
* **35** — PS_A / PS_B: the power inserter (coupler 1, CLPS-3009PI) on 2.1
  makes branch 46; supply C (NEW APLHA 90V PS) on 46.1. The app writes the
  supply's record as Lode does (byte for byte but the cursor and one
  undecoded counter), and draws 46.1 as 35b / 35c (-50.00 -61.00 116.00
  116.00; C, `\04 0%`). 35b asks the keys.
* **36** — H_A / H_B: hc 0 → 2 fills the house list and takes off the
  line's arrow; the inserted line is a new record. The app writes H_B as
  Lode does, byte for byte but the cursor.
* **37** — AL002's supplies are type 5, which WVEXT862 does not list: Lode
  takes 60 V; branch 4's volts and currents are now Lode's (57.21 / 56.68
  / 56.14 / 55.63 at 1.98 A), 0.00 where no supply reaches, NIU `Y`, the
  cab cell in its series' colour. 44 asks about `↕`.
* **38** — AL004_NOTES opened in Lode with the app's notes on 2.1 and 4.13;
  every figure of 38b is the app's.
* **C1** — LG001 11.5 is `2<16>`: the walk passes 11.6 (0 ft on 11.5's
  cable) and 11.7's 200 counts though it is on 104. Fixed.
* **C2** — the pad / EQ labels are untrimmed (`SPB-  10`) until the amp's box
  has been shown, then trimmed (c2, c2b). The app now does the same.
* **C3** — no block on a branch's 0-ft first line (5.1); 22.1's is for being
  the last line of its cable. Fixed.
* **C4** — the older AL004's 43.1: `<NO FWD EQ>` and `<NO RET EQ>`. As the
  app draws them.
* **C5** — `12{6}` is a DC-12 coupler (coupler column), not a 6-port tap; its
  preview draws 6.8's 6-port slot `<43>`, as the app does.
* **N1** — 88 not picked (N1a/N1b); N1b above asks why.
* **N2** — H043A's Test list, 12 yellow lines: the app's.
* **N3 / N4** — the PCD cell shows the other network and line; the status bar
  reads "No Feeder" only with the cursor on it. Now in the app.
* **N5** — the underground housings: rule found (file-formats 3.8); every
  marker on n5a–f and every file's tally match; H043A/B save byte for byte.
* **N6** — TEST_OL2 set byte 519 only; nothing the user sees depends on it.
* **N7** — EQ Manual / Auto / Auto Ex, OP Off / On Fail / On, DEV Total /
  Fwd / Rtn Dev.: the app's lists already.
* **N8** — BH_KEYED: the NC4000 is picked too (0 0 7 0), the FM332 21 21 2 1;
  the app's pick and every tally match.
* **N9 / N10** — Beckley750's six Parameters tabs and AL005's 51 Test lines:
  every field and line is the app's.
* **N11** — no network on an old spec: N11b above asks for a keyed one.
* **N12** — "Not enough taps at node b.n.", red, after the node's tap lines.
  Now in the app.

## Answered 4 Oct (25–33)

25. **Two-branch coupler** — double-clicking either bracket of 4.14's
    `3-<11>{12}` goes into that branch; the wheel turned up on its first line
    comes back to 4.14 with the cursor on ftg; Show Tips is on again after a
    restart. The app now enters the second branch from the second bracket
    (it entered the first); the rest it did already.
26. **`{n}` and `(n)`** — Lode draws four brackets, told apart only by the
    glyph: `<` pointed, `(` with a flat middle, `{` with a notch. `(n)` a
    branch with no footage (4.17's `1(18)`), `{n}` one along the parent's span
    behind (4.4's `12{6}`), `<n>` one along the span ahead (4.14's `<11>`),
    `[n]` the rest. Every bracket on every screenshot since 26 Sep was read
    again, glyph by glyph: all now as the app draws them, and 9.1 is
    `108<10>` with 9.2's power stop (29b) — the power stop does not count.
    6-port slots (the LEQ\RC pads, 6.8's `{43}`) are `{n}` too, and the
    expanded display's supply and pad/EQ lines are in round brackets.
27. **Several taps on one line** — 27a–27d (/23/ /11/ / 4/ on 8.1): every
    figure, each tap's box and the `/` lines were the app's already. With no
    network having a tap that feeds a branch among several, that part is
    dropped.
29. **The block on a 0-ft line** — none on a 0-ft line after a coupler (9.2,
    10.4, 14.5, 20.18, 25.2, 29.3, 29.7, 36.2, 37.2). New: a block on the last
    line of a cable — 5.25 (406, then 414) and 5.27 (414, then 515), its node
    box the short one. The app now draws those; all 28 blocks on 29a–32b
    match figure for figure.
30. **The third count** — still 0 for every active keyed (KERMIT750's
    FM901e-B, FM902B, FM902T, FML332 and FML1G7J on LG001): it is not any of
    them, so it stays 0 in the app. 30a–30e showed more: with "Allow Over
    Equalization" unticked and no EQ that fits, Lode picks no forward EQ
    (`VOID` or nothing in the box, `<NO FWD EQ>` with a reverse-cyan lead-in
    in `/`), and an internal coupler above its active at the same place
    (2.33's MB-JMP over 2.35's FM902T) is red. The app now does all three;
    every figure on 30a–30e matches.
31. **5.29** — the white `(1)` under the node, as the app draws it.
32. **The cyan `(1)`** — the tap's place on the line: `(1)` `(2)` `(3)` on
    27d, each row that tap's port levels. As the app draws it.

## Answered 3 Oct (the morning's 1–24)

1. **Pads and EQs** — picked as the amp is keyed (1a: Flag / CS8 / Flag / 2)
   and again whenever its input changes (1b, ftg 900: 060 / 13 / 190 / 6;
   6b: AL00419 FLAG / SCS6 / 20 / 0 after the Ripple). Recalc changes
   nothing. With "Allow Over Equalization" unticked the return EQ does not
   over-equalize either (1b's 6, not 7). The app now does all of it.
2. **Test lists** — H043B's (2a), two lines: the app's are the same two.
   1c ("Not enough taps at node 1.2.") is a check the app does not make
   yet (part B, N12).
3. **HUMB `<21>`** — keyed on BH, then HUMB loaded (a mismatch). Keyed on
   HUMB, 3a: every figure and `<20>`'s box are the app's.
4. **0 in a spec column** — 0 dB (4a: -48.00 37.00 11.00 11.00 | 44.50
   49.00). With H043A/H043B it also showed a negative coupler figure is a
   gain (BH's FMT Split, -9). The app now reads couplers so.
5. **`/12/`** — as the app draws it, yellow, hc 5 red; every figure of 5.
6. **Ripple mid-cascade** — Cascade Position 1 (the actives before it),
   AL00419 2; its line shows the levels arriving, the return red. The app
   now does the same.
7. **S3's red coupler** — WV750's MULTI OUT is an internal coupler (a node's
   leg coupler) and must sit at an active's place: 100 ft away it is red,
   under the Ripple green (7a/7b). The app now draws it so.
8. **Crossover** — printed seven wide, as Lode does (done).
9. **Mismatched spec sets** — they do not matter; Lode's way is kept.
10. **Reserve Gain** — every BH row 0.00 (10a/10b), as the app reads it.
11. **Actives tab scrolled right** — In and Out at F3–F6, R3, R4 with their
    Out/Loss: now in the app's window, row for row.
12. **Out/Loss** — one byte changed in TEST_OL.atv (518); which byte other
    rows use needs one more test (part B, N6).
13. **Plug-Ins / Configuration Table** — 31 plug-in rows; Quantity 1 beside
    each plug-in named (now shown).
14. **Taps window** — built from your recording: all eleven tabs.
15. **Couplers window** — built: Couplers (-9.00 on FMT Split, as Lode
    shows it) and the four NIU tabs (empty in every file).
16. **Connectors, Series/Colors** — built (16a, 16c).
17. **RA-KIT-40L** — confirmed at row 42.
18. **Bridgers / Feedermakers** — not used: left empty.
19. **Old formats** — you still use them; NPG550's windows recorded (19a–f).
    Reading the oldest actives is the next work item (part B, N11).
20. **LK002's 1.5** — a PCD: Lode writes the network and line it connects to,
    `LK265 1.5` (20.png); PCDs are part B, N3–N4.
21. **BH_TEST.ntw** — see part B, N8.
23. **AL002 / AL003 / AL005** — WVEXT862 (the same files as the pack's) and
    Beckley750 (new): AL005 opens with it, every part resolved, all 22
    actives' pads and EQs matching.
24. **"ntw map AL004"** — a file named in the first sessions; you don't know
    it, so dropped.

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

