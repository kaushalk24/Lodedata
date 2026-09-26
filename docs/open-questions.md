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
4. **Pad/EQ values.** EQs are stored as indexes (AL00416: forward EQ #16 is
   shown as 12, return EQ #3 as 4). The map tag of AL00415 shows forward pad 8,
   EQ `SCS4`, return pad 7, EQ `2`; the file has pads 8 / 7 and EQ indexes
   2 / 1 — so the return EQ shown is index + 1 both times, and the forward EQ
   is a name from a table. Needs: Spec Edit → Actives, Pads/EQs Bank tabs.
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
   node's couplers: 4.24–4.26); a blank. An amplifier node puts its name,
   supply and pad/EQ parts on lines 2–3 (4.24: `[AL00419]`,
   `< SPB-7 ! SEQ-750-0 >`, `A>`, `< SPB-2 ! MEQ-42-2 >`).
   A cyan block sits on lines 4–5 of every node with an amplifier or a
   coupler and of each branch's last node. Checked on 6.9, 4.24, 4.25 and
   4.26 — every number matches:
   * line 1 `[a b c d e f g h]`: aerial distance to the previous active;
     aerial distance to the network start; total distance to the previous
     active or split; total to the previous active; total to the start;
     cable loss at 750 over c, over d and over e. The first five are the
     amplifier info box's distances.
   * line 2 `A-B-C D-E-F homes ftg`: `homes` = housecounts from this node
     on, couplers included; `ftg` = footage since the previous active or
     split on this node's cable (6.9: 894 = the 106 spans, not 6.2's
     121 ft of 114). `A-B-C` = actives from the network start down to this
     node, itself included, `D-E-F` = actives from this node on (itself
     and every branch below), each counted by kind: A, D = bridgers
     (6.9: 1-0-0 = AL00415; 4.24: 2-0-0, 2-3-0 = 4.24 + 20.17, and the
     three LEs 20.6, 20.11, 22.3). The node (Ripple) is not counted. A
     "deepest cascade below" reading gives 2-2-0 at 4.24, not the 2-3-0
     shown.
   Open: (a) B = LEs on the way down is inferred, not yet seen — no node
   shown so far has an LE above it; predicted for branch 22:
   22.3 `[ 74 2994 385 459 3379 6.85 8.45 51.67]` `2-1-0 0-1-0 16 360`,
   22.4 `[ 0 2994 0 0 3379 0.00 0.00 51.67]` `2-1-0 0-0-0 16 0`,
   22.5 `[ 0 2994 80 80 3459 1.42 1.42 53.09]` `2-1-0 0-0-0 8 80`;
   22.3's 360 is also the test of "this node's cable": 22.2 is cab 505,
   the same EX P3 625 U as 22.3's 405 — 385 if the program matches the
   cable rather than the code. (b) What C and F count (0 everywhere in
   AL004). (c) How the program tells a bridger from an LE: no byte of the
   `.atv` records differs between them apart from name, levels and power
   table. (d) What `(1)` counts; AL004 has no node with two taps.
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
