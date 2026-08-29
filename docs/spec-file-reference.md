# Spec file reference

Every spec file is JSON with a small header (`kind`, `name`, `description`,
`version`) plus its payload. Loss figures are keyed by frequency column
(`F1`–`F6` forward, `R1`–`R4` return); a `"*"` key acts as a wildcard for
every column.

Load a whole set from a directory — one file per extension — with
`SpecSet.load_dir(path)`, or point a `.dap` project or `.xsp` Xspec at it.

---

## PARAMETERS — `.par`

The master file. Declares the frequency columns every other file is indexed
by.

| Field | Meaning |
| --- | --- |
| `distance_units` | `feet`, `meters` or `decimeters`; sets the basis for cable attenuation ("per 100 ft", or per 100 m) and loop resistance (per 1000) |
| `signal_display` | `dBmV` or `dBuV` for display; storage is always dBmV |
| `frequencies[]` | `{id, label, mhz, enabled}` — up to six forward, four return |
| `fwd_eq_high` / `fwd_eq_low` | the two columns used to select forward pads and equalizers |
| `rtn_eq_high` / `rtn_eq_low` | the same for the return path |
| `min_tap_output{}` | minimum acceptable forward level at a tap port, per column |
| `tap_window` | dB above the minimum that a tap port may reach |
| `enforce_tap_window` | when true the window is a hard ceiling, not advisory |
| `max_return_tap_input{}` | maximum level a subscriber may need to transmit |
| `return_window` | dB below that maximum still considered normal |
| `set_margin` | out of spec by less than this is yellow; by more, red |
| `max_crossover` | how far forward low may exceed forward high before an in-line equalizer is called for |
| `allow_over_equalization` | may an equalizer slope harder than required be used |
| `default_housing_offset` | dB between module and housing levels, when a device does not state its own |
| `homes_to_ports[]` | `{homes_max, ports}` — the tap sizing table |
| `default_tsg` | tap selection group used when a location does not name one |
| `tap_selection` | `highest_value` (default) or `lowest_value` |
| `powering{}` | supply voltage and rating, minimum device voltage, voltage margin, `stair`/`linear` interpolation, penetration percentage |
| `default_cable` / `default_trunk_cable` / `default_active` / `default_coupler` | what the editing tools reach for |
| `cable_loss_factor` | multiplier on every cable loss, for a design temperature |
| `connector_loss` | dB per connector pair on a span |

## CABLES — `.cab`

| Field | Meaning |
| --- | --- |
| `id`, `description`, `part_number` | identity |
| `atten{}` | dB per 100 distance-units, per column |
| `loop_res` | ohms per 1000 distance-units (powering) |
| `size`, `vop` | informational |
| `price`, `connector_price`, `labor` | costing, per distance-unit |

## TAPS — `.tap`

| Field | Meaning |
| --- | --- |
| `id`, `description`, `part_number` | identity |
| `tsg` | tap selection group, 1–99 |
| `value` | the number printed on the map |
| `ports` | 2, 4 or 8 — drawn as `[ ]`, `( )`, `{ }` |
| `tap_loss{}` | input to a tap port, per column |
| `insertion_loss{}` | input to output (through), per column |
| `self_terminating` | true ends the line; no through port |
| `max_amps`, `resistance`, `power_passing` | powering |
| `price`, `labor` | costing |

## COUPLERS — `.cpl`

Splitters, directional couplers, power inserters and in-line passives.

| Field | Meaning |
| --- | --- |
| `kind` | `splitter`, `dc`, `power_inserter` or `passive` |
| `thru_loss{}` | loss on the through leg |
| `tap_legs` | how many tap legs the coupler has |
| `tap_loss{}` | loss on each tap leg |
| `power_block` | true stops AC here, bounding a powering area |
| `max_amps`, `resistance`, `power_passing` | powering |

Ports are named `THRU`, `TAP1`, `TAP2`, … A balanced two-way splitter is one
tap leg whose loss equals the through loss; a directional coupler has a
low-loss through leg and a high-loss tap leg.

## ACTIVES — `.act`

Levels here are **module** levels; the level shown at the pole is the housing
level, `housing_offset` dB higher on the input side.

| Field | Meaning |
| --- | --- |
| `category` | `node`, `trunk`, `bridger`, `line_extender`, `launch` |
| `gain{}` | full module gain, per column |
| `design_output{}` | the operating output the engine balances to |
| `module_input{}` | nominal / minimum module input |
| `housing_offset` | dB between housing and module |
| `noise_figure{}` | used for the C/N single-unit figure |
| `distortions{}` | `id → {base, ref_level}`; `ref_level: null` means the figure does not derate |
| `pads[]` | stocked pad values, dB |
| `equalizers[]` | `{value, loss{}, part_number}` |
| `outputs[]` | `{name, loss{}}` — a bridger's internal splitter losses |
| `rtn_*` | the same set for the return amplifier |
| `va_pairs[]` | `[[volts, amps], …]` in ascending voltage |
| `max_amps`, `power_passing`, `min_voltage` | powering |

## PERFORMANCE — `.prf`

| Field | Meaning |
| --- | --- |
| `id` | matched against the keys of a device's `distortions` map |
| `addition_factor` | 10, 15 or 20 — the log rule for combining contributors |
| `derate` | dB of degradation per dB of level change; **positive keys off the input level, negative off the output level** |
| `objective` | design target in dB, used for pass/fail reporting |
| `from_noise_figure` | compute the single-unit figure as `noise_constant + input − NF` |
| `noise_constant` | 59 by default |
| `direction` | `forward`, `return` or `both` |

## PRICING — `.prc`

`id` / `part_number` are matched against every device; `material` and `labor`
override the price carried on the device itself.

---

## Project and quick-load files

**`.dap` — project settings**: `spec_dir`, `network_dir`, `report_dir` and an
optional explicit `spec_files` map, so a project always finds its set.

**`.xsp` — Xspec**: up to ten entries, each `{line, name, directory, files}`;
`Xspec.load(path).load_line(3)` loads line 3.

**`.dsn` — network**: `locations[]` and `spans[]`.

| Location field | Meaning |
| --- | --- |
| `kind` | `source`, `active`, `tap`, `coupler`, `power_supply`, `point`, `end` |
| `device` | id of the row in the matching spec file |
| `units` | homes or units fed from this location |
| `tsg`, `tap_ports` | per-location overrides (0 = use the parameters default) |
| `locked` | the automatic tools leave this location alone |
| `pad`, `eq`, `rtn_pad`, `rtn_eq` | manual plug-in overrides (`null` = let the engine choose) |
| `power_supply` | `{id, volts, max_amps}` when a supply is mounted here |
| `power_block` | stops AC at this location |
| `note` | sticky note |
| `x`, `y` | canvas position, in distance units |

| Span field | Meaning |
| --- | --- |
| `parent`, `child` | the locations it joins; the plant must stay a tree |
| `cable`, `length` | cable type and length in distance units |
| `port` | which output port of the parent device feeds this span |
| `extra_loss`, `connectors` | jumpers, splices, connector pairs |
