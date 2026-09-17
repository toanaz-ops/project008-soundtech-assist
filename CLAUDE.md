# PROJECT008-SOUNDTECH-ASSIST — wing-parser: parse & analyse Behringer WING scenes

@memory/MEMORY.md

Global rules load automatically from
`D:\DEV CAVE EP3\shared\harness\RULES.md`. Tier 1 — short on purpose.
Everything not written here is covered globally. Do not restate global rules.

## What this is

Reads a saved WING `.snap` file or talks to a live console over OSC on the
network; classifies what each channel/bus actually is and flags likely
misconfigurations. Desktop UI (`wing-ui`, PySide6) is the primary surface —
CLI/script-only features are not considered done. See `README.md` and
`docs/ROADMAP.md`.

## 🛑 Live console over OSC — read freely, ask before writing

Reading scene state (import, doctor, analyze) from a live WING console is
safe. Writing or pushing any parameter change to a live console reaches real
audio at a venue — ask before writing to a live desk, and never during a show
without explicit confirmation.

## Definition of done

Command and output pasted; docs/spec updated if behaviour changed; commit with
explicit paths.

## Git: GitHub-oriented

`main` chỉ đổi qua PR đã merge trên GitHub; không commit thẳng vào main local.
Mỗi task một nhánh trong worktree riêng, CI (check `test`) phải xanh, người bấm
Merge là ToanAZ. Chi tiết và lệnh cụ thể: `docs/git-workflow.md`.
