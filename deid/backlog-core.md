## BUG: OCR is not accepting images
PNG gives: `Unsupported inline file type: .png`.

This should have been covered in testing, investigate case.


## BUG: Date still giving template default
Input `User_42 from region_BE accessed /profile at 2025-06,` results in `User_42 from region_BE accessed /profile at [DATE_TIME],`.

Expected [DATE_TIME] to never appear and an actual seeded date to be present.

This should have been covered in testing, investigate case.

## FEATURE: add one shot with GLiNER
Add one shot GLiNER support.
Implement only in core (not ui).