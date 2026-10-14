# Remaining frontend restoration — implementation tracker

Scope approved: all items in frontend-unused-features.md except advanced training.

- [x] Five configurable ranked leagues, qualifying games, promotion/relegation,
      league-filtered lists and optional seasons/history.
- [x] Persistent wallet and awards, cosmetic catalog/purchases/unlocks, with free
      customization retained as an option.
- [x] Qualification/round windows, elimination, eligible pairing, advancement and
      tie handling in tournaments; original countdown and elimination UI.
- [x] Replay pause/speed/turn selection with authoritative snapshot restoration.
- [x] Original-style account/community/news screens and current server news.
- [x] Moderator role, role provisioning CLI, kick/ban/mute/revoke, reports and
      audit UI; server authorization and enforcement on every relevant path.
- [x] Configuration, tests, native UI validation, documentation and final builds.

Original game sources/assets stay unchanged. Development schema upgrades discard
incompatible databases without legacy migrations. Historical league thresholds,
round rules and external purchases are not recovered; replacement rules are
explicit and configurable. No advanced-training button/course is added.

Implementation and operating guide: [frontend restoration](frontend-restoration.md).
