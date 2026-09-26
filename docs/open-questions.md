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

* `/n/` 2-port, `[n]` 4-port, `<n>` 8-port taps on the Design screen (8-port
  seen as `<15>` on 11.2).
* `1<18>` is the power inserter; the supply sits inside branch 18.
* Leg designations: `8[2]` downstream high leg, branch low leg; `8-` swaps
  them; `3-<11><12>` puts the high leg on 11; `3=<11><12>` on 12. Keyed as
  `8-` (after the ID) as well as `-8`.

## Open, in the order to settle them

1. **`<n>` versus `[n]` on couplers — mechanism confirmed.** Nothing in the
   file marks it (file-formats 3.7); the program derives it from footage.
   `<n>` when the branch adds no mileage (no footage, or only 1xx cable)
   **and** its first span matches a span already at the coupler's pole — the
   span `BkFeed` (`.2`) / `FwdFd` (`..2`) copy: 6 starts on branch 4's 121
   backward, 11 on its 105 forward, 12 on its 99 backward. Branch 3 is all
   1xx too but hangs off branch 1, which has no spans, so it is `[3]`
   (branch 1 screenshot: `570<2> 570[3] 570[4] 570[5]`).

   Proven by experiment: with 11.1 changed from 105 to 106 in Lode Data,
   4.14 turned from `3-<11><12>` into `3-[11]<12>`, exactly as predicted,
   and branch 11's levels and end line matched the replica.

   Left over: (a) when the coupler sits on a 0-ft branch start, does the
   match follow up to the parent's pole? `screen.py` assumes yes, which draws
   6.1's coupler as `100<7>` (7 runs along branch 4's 156 from the bridger at
   4.4); a parent-only match would give `100[7]`. A branch 6 screenshot
   settles it. (b) `{n}` (backfeed) has not been seen; 6 and 12 run backward
   and are drawn `<`.
2. **8-port tap brackets — closed.** The Design screen draws an 8-port tap
   `<n>` (11.2: `<15>`), like the 6-port-slot pad `<43>`; the preview box
   draws 2/4/8-port as `(17)` `[8]` `{15}`. Both already reproduced.
3. **Power volts** are within 0.02 V; the drop is ~0.5 % more than the photo.
   Currents all match, so it is the resistance — probably a Parameters setting.
   Needs: Spec Edit → Parameters, each tab.
4. **Pad/EQ values.** EQs are stored as indexes (AL00416: forward EQ #16 is
   shown as 12, return EQ #3 as 4). Needs: Spec Edit → Actives, Pads/EQs Bank
   tabs.
5. **Port output colours on the end line.** On branch 6 the 750 and 54 port
   values (21.63, 24.81) are yellow although they are within System Levels;
   the rule behind that is not known. Branch 11's end line (21.55, 20.59,
   38.13, 37.17, with 11.1 at 106 ft) and branch 4's (21.44, 22.41, 36.28,
   35.32) are all green, so it is not a plain threshold on the value.
6. **The "ntw map AL004" file** mentioned earlier has not arrived.
7. **The small 3-option dialog** in the videos, and the multi-line node view
   (the manual says `/` toggles an expanded display).
8. **Keystrokes** — a screen recording (Win + Alt + R) of keying a few nodes.
9. **The power stop field** is confirmed on AL004 only; the older samples set
   it on many more nodes.
