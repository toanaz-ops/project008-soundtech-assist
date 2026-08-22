# Probes behind the C2 design

Throwaway scripts, kept because `2026-08-21-live-watch-design.md` §2 cites their
results and a cited measurement nobody can re-run is not evidence.

All are **read-only**: they read leaves or ask the console to start sending.
None writes a parameter. Each hard-codes the repo path on `sys.path` and takes
the console IP as `argv[1]`, defaulting to the lab rack `192.168.128.28`.

```powershell
python docs\probes\probe5_pollrate.py 192.168.128.28
```

| script | question | answer, and where it landed |
|---|---|---|
| `probe1_subscribe.py` | do `/*S~`, `/*S`, `/*s` reply? | all silent — but **no control**, so the run proves nothing on its own. Superseded by probe 2 |
| `probe2_subscribe_wide.py` | ten subscribe forms, with a control | all silent, control fine. Still **not** proof of absence: an idle desk is silent either way (spec §2.6(1)) |
| `probe3_meters.py` | which `$` keys exist, and does any move? | the `$` key inventory in spec §2.1; none moved |
| `probe4_ppm.py` | is `/$stat/ppm` a meter? is there any meter? | no, and no — spec §2.3 |
| `probe5_pollrate.py` | how fast is a polled watch-list? | 120 leaves in 22 ms; 24 absent addresses cost 20x — spec §2.4, §2.5 |
| `probe6_watch.py` | a working change-watcher; the C2b prototype | loop held 819 rounds / 90 s. Saw 0 events because nothing moved — spec §2.6(2). Also produced the `/main 0` anomaly |
| `probe7_main.py` | was `/main` really absent? | no: 10/10 answered, and 10/10 after a deliberate timeout. `/main` has 4 slots |
| `probe8_flaky.py` | is break-on-first-silence discovery reproducible? | 30/30 correct — so the probe 6 failure is **rare and silent**, which is the whole argument for spec §3.2 |
| `probe9_stripset.py` | can `walk_schema` imply the strip set, given it skips `$` keys? | yes — 1.00 s, 25062 leaves, 0 unresolved, exactly 40/16/4/8/16 contiguous. Spec §3.2 |
| `probe10_name_leaves.py` | does every family answer a bare `name`, and `$name` too? | `name` yes everywhere; **`$name` is NOT universal — /dca/N has none**. Fixes a false claim in `poller.read_labels` |
| `probe11_unreachable_console.py` | what does `--live` report when no console is there? | **FIXED** (was a bug, pre-existing from the C/D cycle): `doctor --live <dead ip>` used to print `No findings.` and exit 0 on an empty scene instead of an error. Now `_load` returns `None` and `doctor` exits 1; the probe prints "Nothing to fix here" |
| `probe12_make_ingest_fixture.py` | is `tests/data/ingest-fixture.xlsx` reproducible? | yes — writes the fixture from scratch via `openpyxl`; the ingest fixture is reproducible, and a measurement nobody can re-run is not evidence |

## Two cautions for whoever runs these next

**Probe 6 needs a human.** It watches for change; if nobody moves a control it
reports zero and that means nothing. Move a fader while it runs.

**Redirecting output needs `python -u`.** Without it the buffered stdout leaves
the log file empty until the script exits, which reads exactly like a hang.
