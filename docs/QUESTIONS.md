# Questions for the user

Updated 4 Oct. Part A is what is still open from the list of 3 Oct (its
numbers kept), part B the questions the answers of 3 Oct raised, part C the
ones the answers of 4 Oct raised — in that order, as you asked. Each says
what to do in Lode Data, what to send, what it settles and what the app does
now. A screenshot means the whole Lode window, info box showing. Where
answers came from: `EVIDENCE.md`.

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

## Part A — still open from the list of 3 Oct

22. **WVBeck750 (yes / no).** You sent it on 29 Sep. May it go into the test
    samples? 34 tests use it.

### Explained again (25–33)

28. **Taking off a tap that feeds a branch.** In the older AL004 (with
    WVEXT862) the tap on 11.16 is drawn `117+` and the one on 11.18 `104+`:
    each feeds a branch (43, 44) straight from its port, with no coupler.
    *Do:* open the older AL004 with WVEXT862, File → Save Network As…
    TAP_A.ntw; put the cursor on 11.16's `117+`, press 0 (Alter), key 0 and
    Enter to take the tap off. *Send:* a screenshot before and after, and
    any box that appears. *Settles:* what becomes of branch 43 — deleted
    with the tap, kept with nothing feeding it, or the tap refused. *App
    now:* kept, fed by nothing (0.00).
33. **The NETWORK MODIFIED menu.** The manual says Num Lock opens a
    "NETWORK MODIFIED" menu (3 Restore, 7 Save, 9 Switch). *Do:* on a copy of
    AL004, change one ftg, then press Num Lock. *Send:* a screenshot of what
    appears (nothing is fine too). *Settles:* whether the menu exists in your
    version and what it offers (the app has none).

### Priority 6 — what Lode writes when saving

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

### Priority 7 — later work (when we get there)

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

## Part B — questions the answers of 3 Oct raised (after part A)

N1. **88 on AL004 4.2.** On 28 Sep, 88 (FML1G7J ALC LE) keyed on 4.2 kept
    0 / SCS6 / 0 / 0, where every other active keyed today was picked at
    once. *Do:* AL004 with WV750-2026, Save As AL004_88.ntw, key 88 on 4.2,
    screenshot with the cursor on it; then change 4.1's ftg 476 → 477,
    screenshot again. *Settles:* whether an ALC line extender is never
    picked or the 28 Sep box was taken before the pick. *App now:* 20 / SCS2
    / 19 / 2 at once.
N2. **H043A's Test list.** *Do:* open H043A_MID with BH1GHzMid, press 5.
    *Send:* every line. *App now:* 12 lines: 2.25 (two), 15.44, 33.6, 38.6,
    38.9, 64.3, 64.5, 66.3, 67.1, 74.2, 89.2.
N3. **H043B's PCD.** *Do:* open H043B_MID, cursor on 1.1's cplr cell.
    *Send:* screenshot of branch 1 lines 1.1–1.8 with the box. *Settles:*
    which network and line it names, and the levels on 1.1 and 1.2 (the app:
    0.00, nothing feeding the first line); also 1.3's bracket — a coupler on
    a 0-ft line of no cable with 234 ft ahead on 119, branch 2 starting 234
    ft (the app: `99[2]`, as S3's 7b). *App now:* draws `(24)`.
N4. **H043A's PCD.** The same on H043A_MID's 1.1; its 1.3 is a 0-ft line on
    19 with a power stop on 1.4 and 625 ft on 19 ahead (the app: `99<2>`).
N5. **Underground housings.** *Do:* H043B_MID, press `/`, go to 1.6, 1.13,
    2.9, 3.7, 13.1 and 7.1. *Send:* a screenshot at each. *Settles:* which
    housing each place takes: Lode's file counts 82 / 11 / 4 / 2 of housings
    1 / 3 / 4 / 5, the app 83 / 10 / 5 / 1 (it gives all five FM902T places
    housing 4 and only 7.1's supply housing 5).
N6. **Out/Loss, a second test.** *Do:* open BH1GHzMid.atv in Spec Edit →
    Actives, Save As TEST_OL2; set row 1's Out/Loss beside "Out - 102" to
    Loss and row 2's beside "Out - 1002" to Loss; Save. *Send:* TEST_OL2.atv.
    *Settles:* where every row's and column's Out/Loss is kept (row 1 Out -
    1002 is byte 518).
N7. **The EQ, OP and DEV drop-downs** on the toolbar. *Send:* a screenshot of
    each list open. *Settles:* what EQ "Auto" can be switched to (the pick
    above happens under Auto).
N8. **BH_TEST.ntw.** It has the same size and branches as H043B_MID — is it
    H043B saved under another name? The file wanted was Q1's keyed network
    (1.1 amp 71, 1.2 190 ft hc 2, 1.3 amp 11) saved: *Do:* key it again,
    File → Save Network As… BH_KEYED.ntw. *Send:* the file. *Settles:* that
    the app writes a new network with two extra frequencies as Lode does.
N9. **Beckley750's Parameters.** *Do:* Spec Edit → Parameters with
    Beckley750. *Send:* all six tabs. *Settles:* its file version (7.0),
    read now as the older layout but not checked against Lode.
N10. **AL005's Test list** with Beckley750. *Send:* every line. *App now:* 51
     lines, beginning "Fslope too low to equalize at 1.1.".
N11. **A network on an old spec.** *Send:* one .ntw designed with NPG550 (or
     bymac862, gefd862, jarr625, npg750, npg860, steph870) and its Test list.
     *Settles:* the oldest actives' reading (decoded next from 19a), checked
     on a real network.
N12. **"Not enough taps at node 1.2."** (1c: 2 homes, no tap). *Do:* AL004
     with WV750-2026, Save As AL004_HC.ntw; set hc 5 on 4.27 (`[17]`, 4-port)
     and hc 3 on 4.29 (`/ 4/`, 2-port); press 5. *Send:* the Test list, every
     line. *Settles:* the line's wording, colour and place in the list, and
     that it is homes against all the line's tap ports (the rule hc turns
     red by). *App now:* hc red, no Test line.

## Part C — new questions from 4 Oct (after part B)

C1. **LG001 11.5.** *Do:* LG001 with WV750-2026 (its own), go to 11.5 (the
    LE `11` with coupler 2 to branch 16, 0 ft on cable 100; 11.6 0 ft, 11.7
    200 ft on 104; branch 16 starts 200 ft). *Send:* a screenshot of 11.3–11.8.
    *Settles:* whether the span ahead counts when it is on another cable than
    the 0-ft coupler line (the app: `2[16]`; it drew `2<16>` before today).
C2. **When the pad and EQ labels lose their spaces.** On 29a (03:34)
    5.23 read `SPB-  10¦  SEQ-750-   6` / `MEQ-42-   2`; on 32a (03:59)
    `MEQ-42-2`. *Do:* close Lode, open it, AL004 with WV750-2026, press `/`,
    go to 5.23: screenshot. Then put the cursor on 5.23's amp cell (its box
    showing), move down a line: screenshot again. *Settles:* whether showing
    the box is what trims them (the app always shows them trimmed).
C3. **A branch's 0-ft first line.** *Do:* AL004 with WV750-2026, `/`, the top
    of branch 5 (5.1, 0 ft with nothing on it, 5.2 on the same cable).
    *Send:* screenshot. *Settles:* whether a branch's first line gets the
    block for being first (the app: yes) — 22.1, the only one seen, is also
    the last line on its cable.
C4. **No EQ on the return, and on the older files.** *Do:* the older AL004
    with WVEXT862, `/`, go to 43.1 (WIFI OMNI; both EQs VOID in its box).
    *Send:* screenshot. *Settles:* the return line with no EQ, and the forward
    one on a file opened rather than keyed (the app: `<NO FWD EQ>` and
    `VOID`).
C5. **A 6-port slot in a coupler's preview.** *Do:* AL004, cursor on 4.4's
    `12{6}` (its preview lists branch 6, with 6.8's `{43}`). *Send:*
    screenshot. *Settles:* how the preview box draws a 6-port slot (the
    app: `<43>`; 2-, 4- and 8-port are `(17)` `[8]` `{15}` there).

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

