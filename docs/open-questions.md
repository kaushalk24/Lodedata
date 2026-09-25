# What is still needed

State after the AL004 pass: a real design (AL004 + WV750-2026) imports
completely and its Design and Power screens are reproduced. What follows is
what is still unknown, and the evidence that would settle each item.

## Reproduced exactly

* Every footage, house count, cable, lv, tap, coupler (with its through-leg
  designation), amplifier, amplifier name and power supply in the file.
* Design screen levels at 750 / 54 / 40 / 5 on every line of branches 3 and 4,
  including the line under the last node and the tap port output shown there.
* Which taps are red (System Levels + tap margin from the Parameters file).
* Power screen currents on all 29 lines of branch 4 (constant-wattage
  interpolation of the power steps).

## Close but not exact

* **Power screen volts** are within 0.02 V of the photo on branch 4, and the
  error is a uniform ~0.6 % too much drop. Currents match, so either the
  loop resistance is corrected somewhere (temperature?) or the photo reading is
  off by a digit here and there. Needs: the Power screen as a real screenshot
  (Print Screen, not a phone photo), or the `.4 Report` powering report saved
  to a file, and a screenshot of Parameters → Powering.

## Not known yet

1. **`<n>` versus `[n]` branch brackets.** Branches 6, 11, 12, 18, 19, 24 of
   AL004 show `<n>`, the rest `[n]`. Nothing stored in the file tells them
   apart, so the program works it out. The manual says `<n>` is a forwardfeed,
   `(n)` a branch with no footage and `{n}` a backfeed. Needs: a sharp
   screenshot of branch 4's coupler column in Design and in Power mode.
2. **The Parameters file beyond levels, supplies and frequencies.** Power
   interpolation setting, tap window, tap selection page, NIU settings. Needs:
   a screenshot of each tab of Spec Edit → Parameters.
3. **Pad and EQ values.** The file stores pads and EQs as indexes (AL00416:
   forward pad 4, return pad 14, forward EQ #16 shown as 12, return EQ #3 shown
   as 4). Needs: Spec Edit → Actives, the Pads/EQs Bank tabs.
4. **In-line devices in the amp column.** Twelve AL004 nodes (e.g. 6.2, 6.8,
   7.2) have something in the amp column that is not an active (codes 75/78).
   Needs: a Design screenshot of branch 6.
5. **The power stop field.** Set on 5.1 and 9.2 in AL004 — consistent with the
   three supplies and the currents — but set on 20-30 nodes in the older sample
   files. Needs: Power screen of branches 5 and 9 showing the `=` marks.
6. **NIU column.** Always `Y` on the photo; its source is not identified.
7. **The amplifier info box.** Its right-hand values were cut off at the screen
   edge in the video; a full screenshot of one would settle the label list.
8. **Keystrokes.** The videos show hands on the keyboard but not which keys.
   A screen recording (Windows: Win + Alt + R) of keying a few nodes, a tap, a
   coupler and an amplifier would pin the key handling down.
