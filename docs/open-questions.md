# What I need from you to finish this

## 1. The documentation site is blocked (hard blocker)

`https://docs.lodedata.com/design/manual/getting-started/` — and every other page
on that host — is refused by this environment's egress proxy (`403` on the
CONNECT tunnel). That is an organisation network policy, not a site outage; I
can't route around it and I shouldn't try. `lodedata.com` is blocked too.

So I have **not** read the manual, and I have not seen a single screenshot of the
application. That is the half of your request I could not start: "go through
every image, understand how the UI and UX is" needs the actual pages.

Any of these unblocks it, easiest first:

* Save the manual pages to a file and upload them — in Chrome, *Print → Save as
  PDF* on each section, or *Save page as → Web page, complete* and zip the
  folder (this keeps the screenshots, which is the important part).
* Or paste the page text into the chat, section by section.
* Or ask whoever administers this workspace to allow `docs.lodedata.com`.

Screenshots matter more than text here. What I most want to see: the main design
window, the device-placement/key-in dialogs for amplifier, tap, cable and power
supply, the spec/equipment editors, the level and design-report views, and the
file-open/spec-attach flow.

## 2. Ground truth to finish the number formats

I have the storage format solved (see `file-formats.md`) but three specific
formulas need one real example each to lock down. Any screenshot or printout
from the running application will do it:

1. **Cable attenuation model.** Open the cable spec editor on `EX .500P3 AER`
   and screenshot it. The file stores `2.16, 0.52` plus `−0.48, −0.16`, and the
   real cable is 1.42 dB/100 ft at 750 MHz. One screenshot tells me what those
   coefficients mean and what frequency they are normalised to, and then every
   cable calculation is exact.
2. **Tap values.** A tap chart or the tap spec editor for `MMT2830` — I need the
   tap loss and insertion loss it shows, so I can locate them in the record.
3. **Amplifier data.** The spec editor for `BLE-7-750PSS`, so I can label the
   `19 / 15 / 21 / 49 / 38 / 43` figures and the response table.

## 3. Ground truth to finish the `.ntw` design file

The obfuscation is fully solved and I can read the plaintext. What's left is the
record layout, and `.ntw` files contain **no text at all** — every part is an
index into the spec files — so I can't bootstrap the layout from strings.

The fastest possible unlock: **build a deliberately tiny design in Lode Data and
send me both the file and the report.** Something like a power supply, one
amplifier, one span of `.500P3` at a known footage, one tap, one terminator.
Then send:

* the `.ntw` file,
* its spec set (all five files),
* and a printed/exported design report or BOM for it (levels, footages, part
  list).

With a known 5-device design I can identify every table in an afternoon. With
only large real-world designs it is guesswork.

Almost as good, and cheaper: take one of the `AL00x.ntw` files you already sent
and export whatever text/CSV/report the application can produce for it. Any
export that lists devices with their part numbers and levels lets me match rows
against the binary.

Also useful: two `.ntw` files that differ by exactly one known edit (save, add
one 26 dB tap, save again). Diffing those pinpoints the tap table immediately.

## 4. Product decisions I need from you

1. **What are you building?** A desktop application (installable, works offline,
   like the original), or a web application (browser, multi-user, hosted)? This
   is the single biggest fork and everything else follows from it.
2. **How far does version 1 go?** Options, roughly in order of effort:
   a. data entry + calculations + reports, no map (spreadsheet-like tree view);
   b. the above plus a schematic canvas you draw the network on;
   c. the above plus geographic basemaps / GIS import, like the real product.
3. **Forward only, or forward + return path?** Return-path (5–42 MHz) design
   roughly doubles the calculation work.
4. **Do you need to write `.ntw` files back**, or is importing them enough and
   your own format is the working format? Import-only is much less risky.
5. **Who are the users** — just you, or a team? That decides whether this needs
   accounts, sharing and a server at all.
