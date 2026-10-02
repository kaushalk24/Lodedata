# Questions for the user

Everything still to be checked in Lode Data to make the replica exact, in
one list, with what to send for each. Kept up to date as answers come in;
the details behind each item are in `open-questions.md` and
`file-formats.md`.

Status: **set A answered** (the user's screenshots of 1–2 Oct, all 18
read); **set A2 below is next** — what set A raised. Answered so far: every
question of the AL004, WVEXT862 and SHINSTON sets up to and including set
A. Where each answer came from: `EVIDENCE.md`.

"Older AL004" below means AL004.ntw opened with the WVEXT862 spec set;
"AL004" the newer one with WV750-2026. A screenshot means the whole Lode
Data window, with the info box in the bottom-right corner showing.

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

## A2. What set A raised (next set)

Your copy of the older AL004 is not the one in the samples pack any more:
its branch 1 has five lines, with an HLN 3842 NODE (70) alone on 1.1; the
pack's has four, an NC4000 (64) and coupler 100<2> both on 1.1. Every
level after the first amplifier matches; the node's 2.50 dB (48.50 against
46.00) is the difference before it.

A6. **Your current older AL004.** *Send:* the file as it is in Lode now —
   File → Save Network As… under a new name (e.g. AL004_SETA.ntw), so your
   own file is left as it is. *Settles:* comparing every number against
   your file, not the pack's. (2 Oct: the AL004.ntw the user attached is
   byte-for-byte the pack's `samples/AL004-WVEXT862/AL004.ntw` — the copy
   with the NC4000 at 1.1 — so this is still to come as AL004_SETA.ntw.)
A7. **A fresh Test list** of that file (screen menu 5), every row.
   *Settles:* the new input/output and cascade lines on your file as it is
   (with the HLN node, 4.13's and 5.12's input lines should be gone) and
   whether 15.4 still reads 23.18 / 16.98.
A8. **The two WIFI OMNI boxes,** 43.1 and 44.1 (cursor on the amp column).
   The replica gives both Cascade Position 4; your 28 Sep box (from 11.18)
   read 4, your 29 Sep one (from 11.16) 3.
A9. **Red cable numbers.** Lode draws 25.2's 505, 5.9–5.22's 438 and
   5.28's 515 red (515 is not red with WV750). *Send:* the info box with
   the cursor on 25.2's 505, and Spec Edit → Cables of WVEXT862 showing
   cable IDs 5, 15 and 38 with every column. *Settles:* what makes a
   cable number red.
A10. **S3 (keyed in Lode).** Open keyed S3.ntw with WV750-2026: does the
    coupler on 1.2 read `100<2>` (the corrected rule: branch 2's first
    100 ft, on 406, as long as 1.2's own span) or `100[2]`, as before?
A11. **Crossover spacing.** Lode prints "Crossover of    3.85" (the number
    seven wide — measured on your Test lists of both AL004s); the replica
    prints "Crossover of  3.85". *Answer:* yes or no to changing it (it
    changes AL004's Test list text, so asked first).
A12. **Custom Cascading** (optional — the rule above fits every box seen).
    *Send:* Spec Edit → Actives → the Custom Cascading tab, with WVEXT862
    and with WV750-2026. *Settles:* the bytes' meaning beyond the
    positions (one bit is not yet known).

## B. Couplers and branches

6. **Two-branch coupler.** On a splitter feeding two branches
   (AL004 4.14, `3-<11><12>`): what do `. ←` and `. →` do, and does a
   double-click on the second bracket enter the second branch?
   *Send:* a note of what happens on 4.14.
   Also: after the mouse wheel (or `. ←`) brings you back from a branch,
   is the cursor on the coupler cell or on ftg (the app: ftg)? And does
   View > Show Tips stay off after Lode is closed and reopened (the app:
   tips come back on reload)?
7. **`{n}` and `(n)`.** The manual lists `{n}` (backfeed) and `(n)` (no
   footage), but Lode draws backward-running and no-footage branches
   `<n>`. *Send:* any screenshot where Lode draws `{n}` or `(n)`, if you
   ever see one.
8. **5xx cable — answered by set A:** the cable does not matter, only the
   span's length (the older AL004's 9.14 is `2<14>` on 404, mileage).

## C. Branches fed from a tap's port (the older AL004's 43 and 44)

9. **Several taps on one line.** When a line has more than one tap, which
   tap feeds the branch, and where does the "Branch:" line sit in that
   tap's box? *Send:* a screenshot of such a line and its tap box.
10. **Clearing that tap.** What does `0` on a tap that feeds a branch do
    (the replica keeps the branch, fed by nothing)? *Send:* a note or a
    screenshot before/after, on a copy of the file.

## D. The expanded display (`/`)

11. (a) Does a 0-ft first line (AL004 22.1) show the cyan block for being
    first, or for being 0 ft on from a coupler? *Send:* the expanded
    display at any of AL004 5.25, 9.2, 10.4, 14.5, 20.18, 25.2, 29.3,
    29.7, 36.2, 37.2.
12. (b) What is the third count in the block's `2-2-0` triples (always 0
    so far)? *Send:* the expanded display of a line below one of WV750's
    FM901e-B, FM901e-T, FM902B, FM902T, FML332 or FML1G7J actives.
13. (c) How Lode tells a bridger from a line extender. *Send:* the Actives
    Specs window's Bridgers tab and Custom Cascading tab.
14. (d) The housing marker where the location's first line carries
    nothing: AL004 5.29 + 5.30. *Send:* the expanded display at 5.29.
15. (e) What the cyan `(1)` under ftg on a tap's line counts. *Send:* the
    expanded display of a line with two or more taps.
16. The small three-option dialog seen in your early videos (possibly
    NETWORK MODIFIED: 3 Restore, 7 Save, 9 Switch). *Send:* a screenshot
    if it appears again.

## E. What Lode writes (saving .ntw files)

17. **TSG, Map, Loc and address.** Where the file keeps them (the replica
    reports them as "not written"). *Send:* two saves of the same network
    from Lode — one before, one after setting a TSG, Map, Loc and address
    on one line (say which line and the values).
18. **A new power supply.** *Send:* two saves from Lode — before and after
    placing one power supply on one line (say which line, which supply).
19. **House lists of new lines.** Which new lines get their house list
    filled in. *Send:* two saves — before and after adding a line with 2
    homes and one with 0.
20. **Counters not decoded** (preamble 23481/23483 and the three pairs at
    36121). Answered by the same kind of before/after saves as 17–19; no
    separate send needed.
21. **Power stops on the older files.** AL002–AL005 set the power stop
    field on many more lines than AL004. *Send:* the Power screen of
    AL002 (any branch) with its spec set, showing where Lode draws `=`.
22. **AL004_NOTES** (optional — SN001 already proved Notes). Open
    AL004_NOTES.ntw with WV750-2026 and check `..+` on 2.1 and 4.13.

## F. Files

23. **WVBeck750 spec set** (.par .atv .tap .cpr .cbl). 34 of the tests
    need it and skip without it.
24. **The spec sets AL002, AL003 and AL005 were designed with**, so they
    can be checked like AL004.
25. **The "ntw map AL004" file** mentioned early on (never arrived).

## G. The repository

26. Earlier commits of `docs/file-formats.md` and
    `tools/lodedata/header.py` quote licence and user ids from the files'
    headers. The current files no longer do (replaced before the server
    zip). Remove them from the repository's history as well? That rewrites
    the branch's history.
