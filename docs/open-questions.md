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
   Still open: (a) 34.6's forward names keep the label's leading spaces
   (`SPB-  16`, `SEQ-750-   4`) where every other name trims them — its node
   record differs from 34.3's only in ids, footage and the values
   themselves; is it the same after reopening the file? (b) Which byte of
   each bank pair is forward. (c) How the program picks them (for designing
   later): the forward EQ is the row whose tilt is nearest what the active
   needs, (In 750 − In 54) − (input 750 − input 54), on all 27 LEs and
   bridgers in AL004; the pad is ⌊input 750 − In 750⌋ on 17 of them and a
   little lower on the rest (6.1, before an `SCS4`, three lower), so the
   EQ's own loss comes off first — the other bank values are not mapped.
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

   Open: (a) whether a 0-ft first node shows the block for being first, or
   for sitting 0 ft on from its coupler (20.18, 0 ft on from 20.17's
   coupler, would tell). (b) What the third count of each triple is (0
   everywhere in AL004). (c) How the program tells a bridger from an LE —
   the `.atv` records differ only in name, levels and power table; the
   replica goes by the name. (d) The housing marker where the location's
   first node carries nothing: 5.29 (333 ft of 415 U, bare) + 5.30 (0 ft,
   a 2-port tap) — the replica puts `(1)` on 5.29; 23.1 should show `(1)`.
   (e) What the cyan `(1)` is; AL004 has no node with two taps. It may be
   the tap selection group in force (the TSG column, blank = the toolbar's
   1).
   The small 3-option dialog in the old videos is still unidentified.
8. **Keystrokes — partly answered.** Design mode's digits are the screen
   menu (`0 Alter`, `5 Test`, `.2 BkFeed`, `..5 Dsmry`; `./ Distance`), `/`
   toggles the expanded display, Esc closes a window. `0` on a tap prompts
   "Enter desired tap {# of ports}.{ID #}:    [home] for list"; Home opens
   Select Tap (a line per tap-file row, parts by port count, tabs 2/4/6/8
   Port, 6-port drawn `{n}`). Entry mode keys values directly. Open: the
   Alter prompt on other columns, and what the Select Tap tabs do.
9. **The power stop field** is confirmed on AL004 only; the older samples set
   it on many more nodes.
10. **Parameters — mapped.** Every setting on the six tabs is located and
    read (file-formats 3.5), proven by the test copy and two save chains.
    Transformer 1's first letter is lost in the file itself: it shares a
    byte with the 900 Series flag. Still to
    confirm: does Strand/Trench Types decide `<n>` for 5xx cable as it does
    for 1xx? (No AL004 branch runs on 5xx alone.)
