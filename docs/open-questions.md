# What is still needed

State after the second AL004 pass: a real design (AL004 + WV750-2026) imports
completely, and every number on the Design-screen screenshots of branches 1, 4,
6, 9, 11, 18, 19, 21 and 22 is reproduced, along with the info boxes.

## Reproduced exactly

* Every footage, house count, cable, lv, tap, coupler (with its leg
  designation), amplifier, in-line Q device, fixed flag, amplifier name and
  power supply in the file.
* Design levels at 750 / 54 / 40 / 5 on every line of the screenshots,
  including the end-of-branch line, tap port outputs and the in-line Q2.
* Tap colours: green in spec, yellow marginal, red out (System Levels + tap
  margin).
* The coupler column, including its four brackets (see 1 below).
* The info boxes: tap port levels, coupler branch preview (start levels and
  the branch table), power supply information, amplifier definition, and the
  node box (address, cable; on an amplifier's node its distances and homes).
  The box is the program's tip: #ffffe1, black text, as wide as its text, in
  the bottom right; View → Show Tips turns it off and on. On a coupler it
  previews one branch — 4.14's `3-[11]{12}` shows "Feeds Branch: 11" only —
  and a double-click enters that branch, as its last line says; on a
  two-branch coupler a double-click on the second bracket enters the second
  branch (the user, 4 Oct). `. ←` / `. →` on one: not asked further (the
  user works with the mouse); the replica keeps `. ←` = back to the parent,
  `. →` = into the first branch.
* Screen colours, measured from the screenshots: text #00bf00, the cab
  column #00ff00, amplifier names white, marginal #ffff00, out #ff0000.
* Power currents on all 29 lines of branch 4.

## Answered by the user

* `/n/` 2-port, `[n]` 4-port, `<n>` 8-port taps on the Design screen (8-port
  seen as `<15>` on 11.2); a 6-port slot `{n}` (4 Oct).
* `1(18)` is the power inserter; the supply sits inside branch 18.
* Leg designations: `8[2]` downstream high leg, branch low leg; `8-` swaps
  them; `3-<11>{12}` puts the high leg on 11; `3=<11>{12}` on 12. Keyed as
  `8-` (after the ID) as well as `-8`.
* Navigation (4 Oct): double-clicking either bracket of `3-<11>{12}` goes
  into that branch; turning the wheel up on its first line comes back to
  the splitter's line with the cursor on ftg. View → Show Tips is on again
  after Lode is restarted.

## Open, in the order to settle them

1. **The bracket around a branch number — closed (4 Oct).** Lode's font
   draws `<` pointed, `(` with a flat middle and `{` with a notch; at the
   screenshots' size all three pass for `<`, and every "`<n>`" read before
   4 Oct was one of the three. Read glyph by glyph on every screenshot since
   26 Sep (85 couplers on AL004, the older AL004, SN001, LG001, S3, the keyed
   BH/HUMB): `(n)` no footage; `{n}` first span as long as the parent's
   nearest span behind (the coupler's own line's first; it wins when both
   match — S3's 1.2, `100{2}`); `<n>` as long as the nearest span ahead;
   `[n]` otherwise. The walk passes 0-ft lines and power stops — 9.1 is
   `108<10>` with 9.2's stop on (29b) as off (SHINSTON3 2); the `108[10]`
   behind the old power-stop rule was branch 9's preview box, which draws
   every branch `[n]`. The walk also passes 0-ft lines on the coupler
   line's cable file index and stops at a 0-ft line on another; the span it
   reaches may be on any cable: the older AL004's 4.14 (410) is `3[11]{12}`
   (4.15 0 ft on 100, SHINSTON3 1c), LG001's 11.5 `2<16>` (11.6 0 ft on
   100, then 200 on 104: c1, 4 Oct), H043B's 1.3 `99<2>` (n3), SN001 18.1
   (442 → 142) `108<19>`.
2. **Tap brackets — closed.** The Design screen draws 2-port `/n/`, 4-port
   `[n]`, 8-port `<n>` (11.2's `<15>`, pointed) and a 6-port slot `{n}` (the
   LEQ\RC pads, 6.8's `{43}`, 36.6's `{40}`, as the manual says); the
   preview box draws 2/4/8-port as `(17)` `[8]` `{15}`. The expanded
   display's amplifier lines: the name in `[ ]`, the supply and the pad /
   EQ parts in `( )`.
3. **Power volts — closed.** Each span's resistance is whole milliohms,
   truncated (feet × µΩ/ft, integer-divided by 1000). All 29 volts and 29
   currents on branch 4 now match exactly, and AL00415 reads 86.78 V 0.79 A
   as on the map. The Parameters tabs have no resistance setting; Power
   Interpolation is Constant Wattage, as already modelled.
4. **Pad/EQ values — answered.** The Actives tab's Fwd Pad / Ret Pad /
   Fwd EQ / Ret EQ columns are bank numbers; LEs and bridgers use Pads/EQs
   Bank 1. A node stores the bank row less one, and the screens show that
   row's label: the info box the label, the expanded display prefix + label
   (file-formats 3.4c). Every pad and EQ on the six amplifiers seen reads
   back as shown (`tests/test_ntw.py`).
   The pair order is proven by the user's edited spec (BRIDGER 61's Ret
   Pad → 2 moved byte +4). 34.6's `SPB-  16` was the program's own state:
   after reopening it shows `SPB-16`, and the spec saved in that session
   carries exactly 34.6's four labels trimmed. How the program picks pads
   and EQs is solved too (file-formats 3.4c). **When** (3 Oct, the user's
   1a/1b and 6b): as an active is keyed, and again for every active whose
   input an edit changes (1.3's ftg 0 -> 900; a Ripple placed upstream of
   AL00419) — Recalc changes nothing, opening a file keeps what it holds.
   With "Allow Over Equalization" unticked neither EQ takes off more tilt
   than is there, return as forward (1b's Return Eq 6, not 7; all 48
   actives of H043A/B). A fibre-fed active is picked too (BH_KEYED's NC4000
   on 1.1, at the 0.00 its line reads: 0 0 7 0), and a bank column with no
   rows gives 255 (VOID). Not explained: WV750's 88 (FML1G7J ALC LE) keyed
   on AL004 4.2 keeps 0 / SCS6 / 0 / 0, and still does after 4.1's ftg
   476 → 477 (N1a/N1b, 4 Oct): Lode does not pick it. Its pads are bank 2
   (NPB-, no Flag row), its EQs bank 1 — which of those stops the pick is
   asked in QUESTIONS N1b; the app picks it (20 / SCS2 / 19 / 2).
5. **Tap and port colours — closed.** The user's recording of Test (screen
   menu 5) lists 37 problems on AL004; the replica produces the same 37 lines,
   word for word, from three checks on each tap's port levels, compared to
   the hundredth:
   * **below min / above max** against System Levels for the node's lv —
     yellow within the tap margin, red beyond;
   * **over window** — a forward port above its minimum plus the tap window
     (750: 12, 54: 16) — yellow. `<43>` at 6.8: 26.82 at 54 is 0.82 over;
   * **crossover** — forward low above forward high by more than Max.
     Crossover (3.00) — yellow on both. 6.9: 24.81 − 21.63 = 3.18, which is
     the end line's yellow 21.63 / 24.81.

   A tap is drawn in its worst colour, each port value in its own. The
   cursor on a yellow tap fills yellow. Select Tap colours candidates by the
   first two checks only (`[11]` and `/ 8/` are crossed over at 6.8 yet
   green there).

   Both settings proven by a second Test with the 5 MHz return window at
   15.50 and Max. Crossover at 3.50: "36 Errors" — a new yellow
   "Tap(5) 0.29 below window at 3.6" (a return port below max − window),
   and the 3.18, 3.34 and 3.40 crossovers gone — all 36 lines reproduced
   word for word. Within a node the list runs
   min/max, then windows, then crossover.
6. **The "ntw map AL004" file** mentioned earlier has not arrived.
7. **Expanded display (`/`) — mostly answered.** Seven lines to a node: the
   node line; four tap-slot lines (port levels coloured per value, or dashes)
   with a cyan `(1)` under ftg; the level passed on (grey, taken after the
   node's couplers: 4.24–4.26); a blank. The replica draws all of it except
   the pad/EQ parts and the housing marker below.
   * **Amplifier, lines 2–3**, from the lv column: `[` + name right-aligned
     in 18 + `]` in olive (#7f7f00), then `<` + supply the same way + `>`
     in white (4.24, 22.3); at column 16 the cyan pad/EQ parts
     `<  SPB-2  ¦  SEQ-750-5  >` — see item 4.
   * **Cyan block, lines 4–5**, six characters right of those, on every node
     with an amplifier or a coupler, each branch's last node, and a branch's
     first node when it is 0 ft (22.1 has one; 34.1 and 4.1, first nodes
     with footage, and 34.4, 0 ft on from an amplifier, have none).
     Checked on 12 nodes — 6.9, 4.4, 4.24–4.26, 22.1, 22.3–22.5, 34.3, 34.6,
     34.9 — every figure (`tests/test_ntw.py`):
     `[%5d%6d%5d%5d%6d%6.2f%6.2f%6.2f]` = aerial distance to the previous
     active; aerial to the start; total to the previous active or split;
     total to the previous active; total to the start; cable loss at 750
     over the third, the fourth and the fifth. Line 2 from column 1:
     bridgers-LEs-? from the start down to the node, itself included
     (34.6: `2-2-0`); the same from the node on, every branch below included
     (4.24: `2-3-0` = 4.24, 20.17 and 20.6, 20.11, 22.3); three spaces;
     homes from the node on in three columns and, with no gap, the footage
     on the node's cable since the previous active or split (4.4: `127886`
     = 127 homes, 886 ft). The footage counts the cable, not the code
     (22.3: 385, with 22.2's 25 ft of 505 counted for 405, the same
     EX P3 625 U). The node (Ripple) is not counted. "Deepest cascade below"
     would give 2-2-0 at 4.24, not 2-3-0.
   * **Housing marker**, white `(n)` in the Node column on line 2: the
     Parameters' Underground Housings. Predicted from 22.3 `(3)` and 22.5
     `(1)`, then seen as predicted: `(1)` at 34.8 and 34.9 (2-port taps on
     401 U), none on 34.3–34.6 (aerial). Nodes 0 ft apart are one location;
     its points (amplifier 16, LE 11, tap 5, 8-port tap 5, coupler 5,
     power supply 30) pick the largest housing whose Minimum Size they
     reach — 22.3: LE 11 + 22.4's coupler 5 = 16 → TV-104 (from 11); a tap,
     5 → TV-60 (from 4). "The smallest that holds them" would make 22.5 a 2.
     The whole rule (4 Oct, H043B's n5a–f and every file's tally):
     file-formats 3.8 "Underground housings".

   Open, each with the evidence that would settle it (asked of the user):
   * (a) **Answered (c3, 4 Oct):** a branch's 0-ft first line gets no
     block for being first (5.1); 22.1's is for being the last line on its
     cable. Was: whether a 0-ft first node (22.1) shows the block for being first
     or for sitting 0 ft on from a coupler. AL004's deciders are nodes 0 ft
     on from a coupler that are not first: 5.25 (after 5.24's coupler, no
     amplifier), 9.2, 10.4, 14.5, 20.18, 25.2, 29.3, 29.7, 36.2, 37.2.
   * (b) What the third count of each triple is: 0 everywhere, and AL004
     uses only 61 (bridger), LEs and the Ripple node. WV750 also has
     FM901e-B, FM901e-T, FM902B, FM902T, FML332 and FML1G7J ALC LE.
   * (c) How the program tells a bridger from an LE. No byte in the active
     record does: bridger 41 and LE 21 carry the same flag bytes (+55,
     +56). The Actives Specs window has a Bridgers tab and a Custom
     Cascading tab, not yet seen. The replica goes by the name.
   * (d) The housing marker where the location's first node carries
     nothing: 5.29 (333 ft of 415 U, bare) + 5.30 (0 ft, a 2-port tap),
     the only such location in AL004. The replica puts `(1)` on 5.29.
   * (e) The cyan `(1)` on a tap's line under ftg: seen on 22.1 (aerial
     404), 22.5, 34.8 and 34.9, one tap each, 1 or 8 homes. Not the homes,
     not the tap cascade (34.9 is the second tap after 34.6 and still reads
     `(1)`). The tap slot or the TSG. The replica prints the slot.
   * The small 3-option dialog seen in the user's old videos: the
     "Network Modified" box, which Num Lock opens after an edit (33.png,
     4 Oct): `[3] Restore`, `[7] Save`, `[9] Switch` and a Close button.
     The app draws it; `[7]` saves. What Restore and Switch do is asked
     (QUESTIONS 33b).
8. **Keystrokes — answered.** Design mode's digits are the screen
   menu (`0 Alter`, `5 Test`, `.2 BkFeed`, `..5 Dsmry`; `./ Distance`), `/`
   toggles the expanded display, Esc closes a window. `0` on a tap prompts
   "Enter desired tap {# of ports}.{ID #}:    [home] for list"; Home opens
   Select Tap (a line per tap-file row, parts by port count, tabs 2/4/6/8
   Port, 6-port drawn `{n}`). The tab marks the port count of the tap
   highlighted; double-clicking a tap places it in the cursor's slot,
   replacing any tap there (the user; `tests/test_ui.py`). Entry mode keys
   values directly. From the user, all built and tested:
   * `0` on ftg, hc, cab or lv starts keying; `.` moves on to the next of
     the four, still keying (`0 150 . 2 . 401`); a field left empty keeps
     its value; lv is the last — `.` there keeps it and goes no further.
     Actives, taps and couplers each take their own `0`. A tap: `0 2 . 4`
     is a 2-port 4, `0 8 . 18` an 8-port 18.
   * `. +` with the cursor on an amplifier's amp column opens Amplifier
     Definition (Power Supply, Amp ID, OK; status line "Enter Amplifier
     name."). The name shows in tap1; a tap placed in tap1 shows instead,
     and the name stays the amplifier's. Any characters. An amplifier not
     yet named is offered the last name given, and `+` / `-` in the field
     step its number (AL00410 → AL00411). A name another active has, in
     any case, closes the window and shows the "Amp Exists" box: "Amplifier
     AL00411 already exists at 34.9." (the user's screenshot).
   * `Insert` adds a 0-ft line above the cursor's, `. Insert` one below;
     every press adds another, the cursor staying on its line. A new line
     takes the cable of the line above it.
   The Feedermaker Networks box in Amplifier Definition (Net 1–4,
   Enter…/Delete) is left out: the user does not use it. The replica's own
   choices where
   nothing says: `+`/`-` step the last run of digits; the name remembered
   is the last one accepted; "Amp Exists" quotes the name as typed; a line
   inserted above a branch's first takes the coupler line's cable.
9. **The power stop field** is confirmed on AL004 only; the older samples set
   it on many more nodes.
10. **Parameters — mapped.** Every setting on the six tabs is located and
    read (file-formats 3.5), proven by the test copy and two save chains.
    Transformer 1's first letter is lost in the file itself: it shares a
    byte with the 900 Series flag. Still to
    confirm: does Strand/Trench Types decide `<n>` for 5xx cable as it does
    for 1xx? (No AL004 branch runs on 5xx alone.)
11. **Saving as .ntw — opens in Lode Data.** File → Save Network writes the
    network back into the `.ntw` it was opened from; Chrome/Edge ask once for
    leave to write it. Save Network As… asks for a file, and the network then
    takes that name and saves there. Nothing about a network is kept once
    the program (or page) closes — the user: no network list, no file,
    no last-opened; each start is empty. Without file access (Firefox) the file
    downloads. The file is built over the one opened (file-formats 3.8), and
    AL004 comes back byte for byte.

    The user opened all seven test files in Lode Data and every change was
    there:
    * T1: 4.1 footage.
    * T2: a line inserted.
    * T3: a new line with a tap.
    * T4: an LE placed and named.
    * T5: a new branch.
    * T6: a line deleted.
    * T7: a branch deleted.

    Lode Data warned "Filename AL004 has changed to AL004_T2_insert. Setting
    all PCDs to open.": the file keeps its own name (44542) and these had been
    saved under other names. A save now writes the name it is saved under.

    Branch numbers (the user): deleting a branch moves the later ones up — with
    2(3), 8(4), 12(5), deleting 2(3) gives 8(3), 12(4). A newly placed
    coupler's branch takes the next number after the highest (AL004: a DC-8
    at 4.9 feeds 46). The replica does both. The new branch's first line
    starts on the coupler line's cable (46.1 on 4.9's 410).

    Save and Save As were tried in Lode Data: it reads the files and shows
    the changes. The file keeps the spec set it was saved with (8 names at
    42366: Parameters … Cables, Prices, Performance, Map Grid); a save
    writes the set now in use. Opened with other files, Lode Data warns
    "Spec File Mismatch", one line per file, and carries on; the replica
    shows the same box.

    A network keyed in from scratch saves too (the user keyed a few lines,
    saved, and Lode Data opened it with them). The user's recording 2
    network, keyed in the replica, gives Lode Data's figures exactly (2.1
    46.41 37.35 17.55 17.19, its /23/ 23.41 14.45 40.45 38.29; 2.2 42.70
    36.25 18.55 17.80; end 41.60 35.55 19.25 18.50). It is now written over
    the program's own empty file (the user's BLANK test, rebuilt byte for
    byte), not the last .ntw opened; only the header's licence and user
    fields still come from that.

    Settled by the user:
    * hc is red when the homes are more than the ports of the line's taps
      together (3 homes and no tap, or a 2-port tap: red; a 4- or 8-port
      tap: green). Done.
    * Lode Data opens a .ntw with no spec set (levels 0.00) and takes the set
      afterwards; so does the replica, and attaching the set reads the
      network again by position.
    * Project Settings on startup ("Show on startup") and the "Errors
      Loading Project" box after its OK: both copied from recording 1.

    * A new network written with blank licence and user fields (NEW_T1)
      opens in Lode Data: it names the spec set it needs and nothing else.
      So a network keyed from scratch saves with no .ntw opened first.

    * Without a spec set an active shows the Active ID of the program's own
      (Unnamed) actives table: 1 – 12 11 … 33H, 13 – 41 61 – 89, 42 – 50
      41 – 49, then ###; taps show ID 0 in their brackets, `[ 0]` `/ 0/`,
      couplers `0[9]`, and an active's box its name, distances, supply and
      homes with type, pads and cascade blank or 0. Done.
    * Delete (the user's recording): a line with a power stop is refused
      ("Cannot delete a line with a power stop."); a line a branch begins
      at asks "Delete Branch(es)?" and OK takes the line and the branch.
      0 on a coupler takes the coupler off and keeps a branch with lines on
      it (`- [55]`); 0 on a branch with nothing on it deletes it. A power
      stop shows `=` in Design; in Powering, + by it takes it off and puts
      it back. Done.
    * Two branches at a line (AL004 4.14, 3-<11><12>): Delete asks
      "Branches 11, 12, begin at this node. Deleting this node will delete
      these branches and all downstream nodes." and takes both; 0 on the
      splitter takes it off both, - <11>  - <12>, keeping them; Delete on
      - <11> then asks the same and takes the line with both (the user).
      Done, levels matching the user's screen from 4.13 to 4.20.
    * Typing a new coupler over one keeps its branch and everything on it:
      12 over AL004 4.26's 8[22] reads 12[22] (the user). Done.
    * S1 – S3 settled the layout of a network keyed from scratch
      (file-formats 3.8).
    * Line extender or amplifier goes by the active's place in the Actives
      table: items 1 – 12 are line extenders, the rest amplifiers (a
      fibre-fed node is neither in the expanded display). The user placed
      WV750's item 40, "FML1G7J ALC LE", on AL004 4.2 and the block counted
      it an amplifier, 1-0-0 9-7-0. The Bridgers and Feedermakers tabs say
      nothing about it. The same test showed the 88 placed holding 0 in its
      pads and EQs (asked again: other actives keyed are picked, 3 Oct) and,
      unnamed, no Amp Name line in its box.

    * The older AL004 opens with the older WVEXT862 spec set (Lode 4's
      files); its 11.16 and 11.18 are taps feeding a branch from the port,
      `117+` and `104+`, and 44.1 reads Lode's 19.90 18.38 36.31 35.43.
      Done (file-formats 3.0 and 3.8).

    * SN001_MID with SHINSTON (SHINN1GHz Mid): its 1.1 holds text at +698
      that moves the rest of the record, so the file was misread and Set All
      Files failed. Read with it: 47 branches, 390 lines, all resolved, and
      it comes back byte for byte; every count table rebuilds from nothing.
      Power supply labels are the whole C string (1A 1B 1C). SHINSTON's .atv
      (11.1) is the current layout up to the in-line devices. Done.

    * SN001 against the user's screenshots: branches 1 and 2 (91 lines),
      4.1, the 13 tap lines of the Test list, four amp boxes and two
      expanded blocks all match. From them: the Configuration Table slot at
      +111 (63U, 11U), the text at +698 is the line's Notes (yellow ♪ after
      the cable), a supply's label in the cplr column, blank pads where the
      bank has none, the node box on a supply's line. Done.

    * SN001's second set (branches 5, 8, 15, 18, 24, 28; three preview
      boxes; 1.2's node box; 5.8's amp box; the Notes window) and the older
      AL004's Test list: every level, port and box matches. From them: the
      preview box's layout (file-formats 3.4), Q1 drawn EQ, 3-digit taps
      `117]`, Fslope/Rslope, `~0` ending each row of a note (now written),
      the node box's distances on a coupler line, and a half that the
      arithmetic leaves a hair under rounding up (9.17's 3.445, "Tap(54)
      6.55"). Lode numbers the tap-fed branches 43 and 44, as stored. Done.

    * The user's third set: Lode Data read the app's notes (SN001's 1.1 with
      a fourth row, a new note on 1.2) and its own save of them is the app's
      byte for byte but for the header's licence fields, the name and the
      cursor; the power stop behind AL004's 108[10] (`<n>` rule above); the
      three half-up values (14.2 34.76, 20.13 21.98, 20.15's 41.23) as Lode
      shows them; Q1 reads EQ on the older AL004 (6.9, 7.6: LEQ-PEA-8); the
      node box lists the distances on a branch's last line (28.16). AL004's
      branches 9, 14 and 20 and the older AL004's 6 and 7 match line for
      line; its AL00416 box names the supply AL004A, as the file holds it.
      Done.

    Still to confirm:
    * set A (the user's screenshots, 1-2 Oct) settled the brackets, the
      cascade position, the red 64 (no active at 11.18) and the Test lines;
      set A2 (2 Oct, AL004_SETA.ntw and 14 screenshots) the rest of it --
      see the points below. What they raised, answered 3 Oct: an excluded
      active mid-cascade counts the actives before it (the Ripple on 4.20
      reads 1, AL00419 after it 2) and its line reads the levels arriving,
      its return checked (25.96 23.48 35.27 34.26, 40 and 5 red); S3's 1.2
      is red as an internal coupler away from any active; crossover lines
      print the figure seven wide, as Lode does;
    * **Cascade Position — solved.** The Actives file's Custom Cascading,
      u16 at +55 of each active (+35 in the older record), the tab's row:
      bit 0 Cust. Casc. (Yes), bit 1 Exclude, bit k + 1 Casc. k Valid
      (k 1-14; the tab's Casc. 15-19 are Invalid on every row seen). Every
      row of WVEXT862's and WVBeck750's tabs reads so (set A2). Positions
      count the actives from the network's node down to this one, itself
      included, but not the excluded: WV750's and SHINSTON's Ripples (Yes,
      Exclude, Casc. 1: 0x0007) are 0, WVEXT862's HLN 3842 NODE (Include,
      0x0005) and NC4000 (No, 0) are 1. So AL004's AL00416 is 1 and the
      older AL004's 2; 6.1 2, 11.10 3, 25.3 4, 23.17 6, 43.1 and 44.1 4
      (set A and A2 boxes, every figure). An active with Cust. Casc. Yes at
      a position not Valid is a Test line, red: "LE  11/5 before/0 after at
      23.17." -- WVEXT862's "11" is Valid at 1-5, 23.17 is 6 with 5 actives
      before and none after. No AL004 or SN001 active is outside its
      positions, and their 68 positions are unchanged. Not seen: an
      excluded active in the middle of a cascade (taken as not counted,
      the tab's word; A13 checks it);
    * **Red cable numbers — solved.** Each cable record ends in ten series
      slots of 23 bytes (+139 past the name: +154 in the older record, +164
      in the current): a Windows colour, four zero bytes, the series' name.
      The Design screen draws the cable number (series·100 + cable ID) in
      its series' colour: WVEXT862's 505, 515 (series 5 of cables 5 and 15)
      and 438 (series 4 of cable 38) red, 404-415 0,200,0; WV750's all
      0,255,0 (its 515 green); SN001's 15.29 "10" 0,200,0 between 0,255,0
      140 and 40. With the cursor on any of ftg, hc, cab or lv, Lode lights
      all four, the cable cell in that colour; the line's box adds the
      series' name from column 15 ("EX P3 625 U    Dual New Build", "DROP
      RB 700 A  Upgrade");
    * **The Test's rounding — solved.** The Test reads a port as Lode
      rounds it, a half added and the rest of the hundredths dropped: at or
      above zero that is the screen's figure, below zero a cent higher. The
      older AL004's 15.4 port at 870, -4.191, is -4.19 on the screen and in
      its box but -4.18 to the Test: 23.18 below min, and 16.98 at 550, a
      crossover of 8.06 (Lode's list twice, 1 and 2 Oct). Changes only
      lines whose port is under zero: none on AL004 or SN001; AL002 21.7,
      AL005 23.8 and 14 of AL003's with WV750 now read a cent lower;
    * **Actives' inputs and outputs — solved.** "870 input 10.97 to LE at
      4.13.": the input less the active's forward pad and EQ loss (as its
      Pads/EQs bank holds them) under its In; "40 output 36.64 from LE at
      25.3.": its Out less the return pad and EQ under the level the line
      needs. The figure is the line's level, printed seven wide; the
      failing levels and the active's ID are drawn red (4.13: 10.97, 24.90
      and 61; 25.3 all five and 11), not the whole line; all of them red
      in the Test list, ahead of the line's tap lines. In at 550 is +127 of
      the older record (14.1 on the LEs: 25.3's 20.98 less its 10 pad).
      Exactly the older AL004's 12 such lines; none on AL004 or SN001
      (their closest passes are 0.01 dB). This replaces the app's earlier
      stand-in ("input below the module input", the whole line red);
    * where the Branch: line sits in the tap box, and which tap feeds the
      branch when a line has more than one;
    * what 0 on a tap feeding a branch does — **answered** (28A/28b, 33,
      4 Oct): Lode asks "Deleting Branch — Deleting this branch will delete
      all downstream design. Continue?" (Yes / No); Yes takes the tap off
      and branches 43 and 44 stay, fed by nothing. The app does the same;
    * the older AL004's Test list — all 94 lines, in Lode's order, every
      line (twice: 1 Oct, and 2 Oct from AL004_SETA). Its five crossovers:
      WVEXT862 holds Max. Crossover 0.00, a limit like any other;
    * the 550 column — **built**: F3 = 550 is the Parameters' third forward
      frequency, drawn after the cplr[branch] columns; cables, couplers and
      taps carry it in slot 2 of their loss blocks, in-line devices as their
      fifth loss, the older .atv's actives In at +127 and Out at +151. All
      57 values on the screenshots of branches 4, 6, 7, 11, 43 and 44 match,
      and all 14 Tap(550) lines. Not seen: a tap out at
      550 alone (its colour is taken to be its worst port's, as at the other
      frequencies); where a Lode 12 .atv keeps an active's F3 levels;
    * 23481/23483 and the three pairs at 36121;
    * which new lines get their house list filled in — **answered** (H_A /
      H_B): every line whose house count is changed to some homes, and a
      new line's record (file-formats 3.8). An hc edit also clears the
      line's fixed arrow (36.png);
    * where TSG, Map, Loc and address go (listed as not written; QUESTIONS
      34, step by step);
    * a new power supply's record — **answered** (PS_A / PS_B, file-formats
      3.8 "A new power supply"); how the supply is keyed in Power mode is
      asked (QUESTIONS 35b);
    * Power mode on the older files (37.png, AL002 branch 4): a supply type
      the spec set does not list (AL002's type 5, WVEXT862 lists 1–3) is
      taken as 60 V — branch 4 then reads Lode's 57.21 / 56.68 / 56.14 /
      55.63 V at 1.98 A; a line no supply reaches reads 0.00; NIU `Y`; the
      cab cell in its series' colour. The `↕` after 4.4's amplifier is not
      explained (QUESTIONS 44);
    * "Not enough taps at node b.n." — red, in the Test list after the
      node's tap lines, when the homes are more than the line's tap ports
      (n12a/b, 1c);
    * the cursor Lode saves at 41425 (QUESTIONS 43).
