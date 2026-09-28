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
* The coupler column, including `<n>` versus `[n]` (see 1 below).
* The info boxes: tap port levels, coupler branch preview (start levels and
  the branch table), power supply information, amplifier definition, and the
  node box (address, cable; on an amplifier's node its distances and homes).
  The box is the program's tip: #ffffe1, black text, as wide as its text, in
  the bottom right; View → Show Tips turns it off and on. On a coupler it
  previews one branch — 4.14's `3-[11]<12>` shows "Feeds Branch: 11" only —
  and a double-click enters that branch, as its last line says. Still to
  confirm: on a two-branch coupler, what `. ←` / `. →` do (the replica keeps
  `. ←` = back to the parent, `. →` = into the first branch), and whether a
  double-click on the second bracket enters the second branch.
* Screen colours, measured from the screenshots: text #00bf00, the cab
  column #00ff00, amplifier names white, marginal #ffff00, out #ff0000.
* Power currents on all 29 lines of branch 4.

## Answered by the user

* `/n/` 2-port, `[n]` 4-port, `<n>` 8-port taps on the Design screen (8-port
  seen as `<15>` on 11.2).
* `1<18>` is the power inserter; the supply sits inside branch 18.
* Leg designations: `8[2]` downstream high leg, branch low leg; `8-` swaps
  them; `3-<11><12>` puts the high leg on 11; `3=<11><12>` on 12. Keyed as
  `8-` (after the ID) as well as `-8`.

## Open, in the order to settle them

1. **`<n>` versus `[n]` on couplers — closed.** Nothing in the file marks it
   (file-formats 3.7); the program derives it from footage. `<n>` when the
   branch adds no mileage (no footage, or only 1xx cable) **and** its first
   span matches the nearest span behind or ahead of the coupler on the
   **parent branch** — the span `BkFeed` (`.2`) / `FwdFd` (`..2`) copy: 6
   starts on branch 4's 121 backward, 11 on its 105 forward, 12 on its 99
   backward. Evidence:
   * branch 1: `570<2> 570[3] 570[4] 570[5]` — 3 is all 1xx but branch 1 has
     no spans;
   * 11.1 changed 105 → 106 in Lode Data turned 4.14 into `3-[11]<12>`;
   * branch 6: `100[7]`. 6.1 is bridger AL00415 at 4.4's pole and 100 its
     internal DC-12; 7 runs as a second cable along branch 4's 156 (the user's
     map confirms it), but only branch 6's own span, 121, is compared.

   Not seen yet: `{n}` (backfeed) — 6 and 12 run backward and are drawn `<`.
   Nor `(n)`, the manual's "no footage": 12.11 draws AL004's no-footage
   branches 2, 18, 19 and 24 as `<n>`. Asked the user whether either
   appears at all.
2. **8-port tap brackets — closed.** The Design screen draws an 8-port tap
   `<n>` (11.2: `<15>`), like the 6-port-slot pad `<43>`; the preview box
   draws 2/4/8-port as `(17)` `[8]` `{15}`. Both already reproduced.
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
   and EQs is solved too (file-formats 3.4c) — the replica uses it for an
   amplifier with none stored, i.e. one placed in the replica.
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

   Open, each with the evidence that would settle it (asked of the user):
   * (a) Whether a 0-ft first node (22.1) shows the block for being first
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
   * The small 3-option dialog seen in the user's old videos (earlier
     session; the videos are no longer here). Possibly the manual's
     NETWORK MODIFIED menu (3 Restore, 7 Save, 9 Switch), which Num Lock
     opens.
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
    takes that name and saves there. The file used for each network is
    remembered across reloads. Without file access (Firefox) the file
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
    2(3), 8(4), 12(5), deleting 2(3) gives 8(3), 12(4). The replica does the
    same. Still to confirm:
    * the number a newly placed coupler's branch gets: the user's example
      reads "2(4)" when 2 is put back above 8(3); the replica gives the next
      number after the highest;
    * what Lode Data writes when it saves one of these files itself;
    * which new lines get their house list filled in;
    * the four undecoded preamble blocks;
    * where TSG, Map, Loc, address and notes go (listed as not written);
    * a new power supply's record;
    * a network started in the app needs a file to build on: an empty network
      saved from Lode Data.
