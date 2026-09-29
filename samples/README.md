Put real Lode Data files here to run the checks against them.

    samples/
      AL004-WV750/      AL004.ntw + WV750-2026.par .atv .tap .cpr .cbl
      AL004-WVEXT862/   AL004.ntw (the older one) + WVEXT862.par .atv .tap .cpr .cbl
      SN001-SHINSTON/   SN001_MID.ntw, SN001_NOTES_test.ntw (Lode Data's save)
                        + "SHINN1GHz Mid".par .atv .tap .cpr .cbl
      partest/          the Parameters test copies (paratest.par, s1-s8, v1-v10,
                        act.atv)
      KERMIT750-2026.*  WVBeck750.*    (both spec sets: tests/test_import.py,
                                        tests/test_entry.py)

Anything under this directory is found automatically, and `pytest` then runs
the checks that read real files. Without them those checks are skipped and the
rest of the suite still passes.

Point somewhere else with `LODEDATA_SAMPLES=/path/to/files ./run-tests.sh`.

This directory is kept out of the repository -- your files stay private.
