## BUG: OCR is not accepting images
PNG gives: `Unsupported inline file type: .png`.
Investigate — should have been covered in testing.


## BUG: Incomplete PII removal
Three confirmed gaps:

- **URL not fully replaced** — e.g. `https://track.everything.biz/user/d-douglas-99?session=88221` → only domain changed, path/params left intact. At 100% strength the full URL should be unrecognizable.
- **Informal/relative dates not replaced** — e.g. `Last Tuesday`, `2025-06` output as `[DATE_TIME]` template instead of a fake replacement value.
- **Addresses/locations not tracked** — e.g. `1428 Elm Street`, `500 Oracle Parkway` not detected or replaced.


## FEATURE: add one shot with GLiNER
Add GLiNER as a standalone one-shot DeID model (Python only).
Architecture must support downloading multiple one-shot models.


## FEATURE: Support pronouns
Research needed before implementation.
Currently `he`/`she` pronouns are not handled. Add optional config to remap pronouns consistently with replaced entities.


## BUG: build process fails
App gives "“PIIPAYA” is damaged and can’t be opened. You should move it to the Trash.".


Can't we simply release the locally build version instead? This whole build setup seems too fragile. Adjust the flow to release a locally build file. Fully autonomous