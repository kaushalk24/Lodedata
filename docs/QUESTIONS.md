# Questions for the user

Everything still to be checked in Lode Data to make the replica exact, in
one list, with what to send for each. Kept up to date as answers come in;
the details behind each item are in `open-questions.md` and
`file-formats.md`.

Status: **paused** at the user's request (after the third SHINSTON set).
Answered so far: every question of the AL004, WVEXT862 and SHINSTON sets
up to and including SHINSTON3 (brackets, Notes, preview box, EQ, slope
lines, half-cent rounding, node box, cascade on AL004, supply labels, ...).

"Older AL004" below means AL004.ntw opened with the WVEXT862 spec set;
"AL004" the newer one with WV750-2026. A screenshot means the whole Lode
Data window, with the info box in the bottom-right corner showing.

## A. The older AL004 (next set — asked, not yet answered)

1. **Cascade position.** Lode reads 2 on AL00416 (4.13), 3 on 43.1 and
   4 on 44.1; the replica 1, 3 and 3.
   *Send:* the amp box (cursor on the amp column) of 1.1 (NC4000),
   6.1 (AL00415) and 11.10 (AL00419).
2. **The red "64" on 11.18.** The file has no active on that line.
   *Send:* the cursor on that 64, and the box it shows.
3. **"870 input … to LE", "40 output … from LE", "LE 11/5 before/0
   after".** 13 lines of its Test list the replica does not make yet.
   *Send:* every Parameters tab with WVEXT862 attached; the amp box of
   25.3 and of 23.17.
4. **15.4.** Lode's Test list says "Tap(870) 23.18 below min at 15.4",
   the replica 23.19 — 0.006 dB apart somewhere on branch 15.
   *Send:* the Design screen of branch 15 (550 column showing), and the
   tap box of 15.3 and of 15.4.
5. **Brackets no screenshot has shown yet.** The bracket rule now drawn:
   *Send:* the Design screen of
   * AL004 branch 5, lines 15–22 (replica: 5.19 `100<29>`);
   * older AL004 branch 16, first lines (replica: 16.4 `8[17]` — the
     power stop is on the coupler's own line);
   * older AL004 branch 9, first lines (replica: 9.1 `108<10>`);
   * older AL004 branch 5 around 5.19 (replica: `100<32>`).

(The 550 column itself and its 14 "Tap(550)" lines need nothing from you:
the values are in the spec files. They come with this set.)

## B. Couplers and branches

6. **Two-branch coupler.** On a splitter feeding two branches
   (AL004 4.14, `3-<11><12>`): what do `. ←` and `. →` do, and does a
   double-click on the second bracket enter the second branch?
   *Send:* a note of what happens on 4.14.
7. **`{n}` and `(n)`.** The manual lists `{n}` (backfeed) and `(n)` (no
   footage), but Lode draws backward-running and no-footage branches
   `<n>`. *Send:* any screenshot where Lode draws `{n}` or `(n)`, if you
   ever see one.
8. **5xx cable.** Does a branch starting on 5xx cable along its parent's
   span get `<n>`, as 1xx does? (Parameters, Strand/Trench Types.)
   *Send:* only if you come across one.

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
