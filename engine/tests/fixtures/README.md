# Portrait Fixtures

Most Analysis V2 tests use synthetic images so CI does not depend on private portraits.

To add real regression fixtures, place small consented portraits in this folder and name them by scenario, for example:

- `portrait_closeup_01.jpg`
- `half_body_01.jpg`
- `full_body_01.jpg`
- `hard_background_skin_color_01.jpg`

Keep files under 1200 px on the longest side, avoid personal metadata, and add the expected debug outputs or assertions in a dedicated test.
