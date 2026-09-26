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
5. **Port output colours on the end line.** On branch 6 the 750 and 54 port
   values (21.63, 24.81) are yellow although they are within System Levels;
   the rule behind that is not known. Branch 11's end line (21.55, 20.59,
   38.13, 37.17, with 11.1 at 106 ft) and branch 4's (21.44, 22.41, 36.28,
   35.32) are all green, so it is not a plain threshold on the value. The
   same unknown yellow is on 6.8's `<43>` (LEQ\RC PAD 13, port levels 26.54
   26.82 39.23 36.85 — within System Levels); the replica draws it green.
   Lead from the System Levels tab: the tap windows (750: 12, 54: 16; 40: 16,
   5: 16). Read as "a port may be at most min + window" (lv 0: 29 at 750, 26
   at 54), `<43>`'s 26.82 at 54 is the only port above its window among all
   13 taps seen, and it is the only unexplained yellow tap. But it does not
   explain branch 6's yellow 21.63 / 24.81, and Enforce Tap Window is off.
   Not applied until confirmed.
6. **The "ntw map AL004" file** mentioned earlier has not arrived.
7. **The small 3-option dialog** in the videos, and the multi-line node view
   (the manual says `/` toggles an expanded display).
8. **Keystrokes** — a screen recording (Win + Alt + R) of keying a few nodes.
9. **The power stop field** is confirmed on AL004 only; the older samples set
   it on many more nodes.
10. **Parameters fields not yet proven** (file-formats 3.5). The test copy
    placed NIU, points, cascades, lines per form, replacement cables,
    overvoltage, over-equalization, tilts and the amperage limits. Left:
    eight fields that all saved as 1 (or 1 → 2) — Distance Units, Signal
    Display, Show Count Types, 800 Series, EQ Placement, Optimization,
    Enforce Tap Window, Flag Hi/Lo Tilt — over 1138, 1142, 1482, 1510, 3904,
    3914, 6001, 6514. A chain of saves reverting one field at a time settles
    them. Also: does Strand/Trench Types decide `<n>` for 5xx cable as it does
    for 1xx? (No AL004 branch runs on 5xx alone.)
