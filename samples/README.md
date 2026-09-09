Put real Lode Data files here to test the readers against them.

    samples/
      KERMIT750-2026.par  .atv  .tap  .cpr  .cbl
      WVBeck750.par  .atv  .tap  .cpr  .cbl
      AL005.ntw

Anything under this directory is found automatically (nested folders are fine),
and `pytest` then runs the checks that read real spec files. Without them those
tests skip and the rest of the suite still passes.

Point somewhere else with `LODEDATA_SAMPLES=/path/to/files pytest -q`.

This directory is gitignored — your spec files stay out of the repository.
