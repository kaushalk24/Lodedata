# Lodedata

Reverse engineering of the Lode Data Design Assistant file formats, and the
groundwork for an HFC network design application that can read them.

## Status

**Solved**

* The 512-byte header shared by every Lode Data file — magic, format version,
  authoring app version, licence id and user id.
* The `.ntw` network-file obfuscation: a fixed 100-byte **additive** keystream,
  key recovered and verified identical across all sample files. Design payloads
  can be read as plaintext.
* The equipment spec files (`.cbl`, `.cpr`, `.atv`, `.tap`) — record strides,
  part-number fields and the `int32 × 1e6` fixed-point number convention.
  Cable loop-resistance values decode to exactly the published figures for the
  real Commscope/other cables, which confirms the decode.

**Not solved yet** — both blocked on inputs I don't have; see
[`docs/open-questions.md`](docs/open-questions.md)

* The `.ntw` record layout (design files contain no text, only indices into the
  spec files, so there is nothing to bootstrap from without a known-content
  sample).
* The cable attenuation, tap-loss and amplifier-gain formulas — the numbers are
  readable, their exact meaning needs one screenshot each from the application.
* The application's UI and UX — `docs.lodedata.com` is blocked by this
  environment's network policy, so the manual has not been read.

## Layout

```
docs/file-formats.md     what the bytes mean, and how each claim was verified
docs/open-questions.md   what I need from you to finish
tools/lodedata/          Python reader library and CLI
```

## Usage

```sh
PYTHONPATH=tools python3 -m lodedata info   AL005.ntw
PYTHONPATH=tools python3 -m lodedata decode AL005.ntw AL005.plain
PYTHONPATH=tools python3 -m lodedata spec   KERMIT750-2026 --json
```
