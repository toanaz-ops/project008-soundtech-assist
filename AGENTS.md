# Project agent rules

- UI styling: the token table `wing_parser/ui/theme/tokens.py` generates
  `theme.qss` + `chrome.qss` in `wing_parser/ui/resources/`. Never call
  `setStyleSheet()` inside a widget. No colour literal, font family, size
  or weight outside `wing_parser/ui/theme/` (the house-style tests
  enforce this). Icons come from `qtawesome`; never emoji. Authority for
  any PySide6 work: the `pyside6-ui-quality` skill plus the in-repo
  house-style plan
  `docs/superpowers/plans/2026-08-26-gui-house-style-wave1b.md`.
  **GUI work is not reported without a picture**: every visual change
  ends with a screenshot the author has looked at, not a claim.
