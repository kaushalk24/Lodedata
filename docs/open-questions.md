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
  the branch table), power supply information, amplifier definition.
* Power currents on all 29 lines of branch 4.

## Answered by the user

* `/n/` 2-port, `[n]` 4-port, `<n>` 8-port taps on the Design screen.
* `1<18>` is the power inserter; the supply sits inside branch 18.
* Leg designations: `8[2]` downstream high leg, branch low leg; `8-` swaps
  them; `3-<11><12>` puts the high leg on 11; `3=<11><12>` on 12. Keyed as
  `8-` (after the ID) as well as `-8`.

## Open, in the order to settle them

1. **`<n>` versus `[n]` on couplers.** Nothing in the file marks it (see
   file-formats 3.7); the program derives it. The branch 1 screenshot shows
   `570<2> 570[3] 570[4] 570[5]`, which broke the old rule ("`<n>` when the
   branch has no footage on non-1xx cable"): branch 3 is 1134 ft, all on
   cable 100, yet `[3]`.

   What sets 3 apart from `<6>`, `<11>`, `<12>` (also all 1xx) is where its
   spans go. `BkFeed` (`.2`) and `FwdFd` (`..2`) copy the parent's spans, and
   6, 11 and 12 start on exactly such a copy: 6 on branch 4's 121 backward,
   11 on its 105 forward, 12 on its 99 backward. Branch 3 hangs off branch 1,
   which has no spans at all. The rule now in `screen.py`, which fits all
   sixteen branches seen: `<n>` when the branch adds no mileage (no footage,
   or only 1xx cable) **and** its first span matches a span already at the
   coupler's pole (following a 0-ft branch start up to the parent's pole).
   It differs from the old rule only on branch 3.

   Still unproven: whether the program really compares footages, or uses
   something else that happens to separate 3 from 11 (e.g. "the parent has
   footage"). The test: on a copy of AL004, change 11.1's footage from 105 to
   106 and look at 4.14 — a footage rule turns `3-<11><12>` into `3-[11]<12>`.
   Also open: whether `{n}` (backfeed) is ever drawn; 6 and 12 run backward
   and show `<`.
2. **8-port tap brackets.** The Design screen drew the 6-port-slot pad as
   `<43>`. No 8-port tap has been seen on the main screen yet (the preview box
   draws 8-port as `{n}`). Branch 22 node 5 and branch 11 node 2 carry 8-port
   taps.
3. **Power volts** are within 0.02 V; the drop is ~0.5 % more than the photo.
   Currents all match, so it is the resistance — probably a Parameters setting.
   Needs: Spec Edit → Parameters, each tab.
4. **Pad/EQ values.** EQs are stored as indexes (AL00416: forward EQ #16 is
   shown as 12, return EQ #3 as 4). Needs: Spec Edit → Actives, Pads/EQs Bank
   tabs.
5. **Port output colours on the end line.** On branch 6 the 750 and 54 port
   values (21.63, 24.81) are yellow although they are within System Levels;
   the rule behind that is not known.
6. **The "ntw map AL004" file** mentioned earlier has not arrived.
7. **The small 3-option dialog** in the videos, and the multi-line node view
   (the manual says `/` toggles an expanded display).
8. **Keystrokes** — a screen recording (Win + Alt + R) of keying a few nodes.
9. **The power stop field** is confirmed on AL004 only; the older samples set
   it on many more nodes.
