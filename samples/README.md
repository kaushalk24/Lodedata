Put real Lode Data files here to run the checks against them. They come in
`lodedata-samples.zip`: unzip it in the repository root.

    samples/
      AL004-WV750/      AL004.ntw + WV750-2026.par .atv .tap .cpr .cbl
      AL004-WVEXT862/   AL004.ntw (the older one) + WVEXT862.par .atv .tap .cpr .cbl
      SN001-SHINSTON/   SN001_MID.ntw, SN001_NOTES_test.ntw (Lode Data's save)
                        + "SHINN1GHz Mid".par .atv .tap .cpr .cbl
      partest/          the Parameters test copies (paratest.par, s1-s8, v1-v10,
                        act.atv)
      KERMIT750/        KERMIT750-2026.par .atv .tap .cpr .cbl
      designs/          AL002.ntw AL003.ntw AL005.ntw (the older designs)
      keyed/            BLANK_test.ntw (Lode's empty network), S1-S3.ntw (keyed
                        from it, one step each)
      app-saved/        NEW_T1.ntw, AL004_NOTES.ntw, SN001_NOTES.ntw -- files the
                        app wrote and the user opened in Lode Data

    Still missing: WVBeck750.par .atv .tap .cpr .cbl -- tests/test_import.py
    and tests/test_entry.py need it with KERMIT750 and skip without it.

`docs/EVIDENCE.md` says where each file came from and what it proved.

Anything under this directory is found automatically, and `pytest` then runs
the checks that read real files. Without them those checks are skipped and the
rest of the suite still passes. `python tools/regression.py` opens every
`.ntw` here with every spec set here.

Point somewhere else with `LODEDATA_SAMPLES=/path/to/files ./run-tests.sh`.

This directory is kept out of the repository -- your files stay private.
