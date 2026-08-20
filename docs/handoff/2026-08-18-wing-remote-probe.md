# WING remote control — what is and is not derivable here

**Date:** 2026-08-18 · Written so nobody spends a second session on the two
dead ends below. Same purpose and shape as
`2026-08-17-limiter-token-probe.md`.

## Why this was probed

Sub-project C — read a running WING over the network — needs two separate
things, and they were being treated as one:

1. **A transport.** Where to send, over what, on which port.
2. **An address vocabulary.** What to send: the OSC address for a channel's
   fader, a send's mode, a mute.

`2026-08-18-desktop-app-complete.md` originally said the whole lot "has to come
from outside this repo". **That was wrong about the first half**, and the error
came from citing a knowledge-base summary instead of opening the manual sitting
in `user-files/`. Corrected here.

## What is now known — the transport, from the manual

`user-files/User-Manual_WING-series_2025-10-20.pdf`, 167 pages. Page 50, the
`SETUP → REMOTE` section:

| Fact | Where |
|---|---|
| OSC remote control runs on **IP port 2223** | p50, the REMOTE LOCK sentence |
| A second remote-control channel runs on **IP port 2222** | same sentence |
| **REMOTE LOCK** is a console setting that blocks remote control on **both** ports | same sentence |
| **Up to 16 devices** may remote-control one WING at once | p50, NETWORK paragraph |
| The console must be wired to the switch or router by Ethernet; clients may be wireless | p50 |
| Network mode is **DHCP or Static IP**, chosen on the console | p50 |
| The vendor's own remote clients are WING Edit (desktop), WING Copilot (mobile), WING Q (mobile, bus/matrix only) | p50 |

**A search trap worth knowing:** the manual spells the second port's protocol
**"TPC"**, not "TCP". Searching the PDF for "TCP" returns nothing at all. It is
almost certainly a typo for TCP, but that is an inference, not something the
document states — do not write "TCP" into code comments as though the manual
said it.

**Consequence for the app.** Two separate things can refuse a write, and a write
path must account for both:

- **REMOTE LOCK**, a console setting, from the manual above.
- **`ce_data.osc.ronly`**, a flag inside the scene file, probed 2026-08-18:
  both sample files hold exactly `{"ronly": false}`.

Whether these are the same switch seen from two sides is **not established**.
Nobody has toggled REMOTE LOCK and re-saved a scene to see whether `ronly`
moves. That is a one-minute experiment for ToanAZ at the console and it settles
the question; until then, treat them as two independent conditions.

## What is still missing — the address vocabulary

**It is not in the manual.** Of 167 pages, exactly **one** mentions "OSC" at
all, and only to say the port can be locked. There is no address table, no
address example, and no reference to a separate protocol document. Searching
for `/ch/` across every page returns nothing.

**It is not extractable from `WING-Edit.exe` by string scan.** The binary is a
93 MB PE image whose payload is packed or compressed: a full ASCII scan finds
962 slash-delimited strings in the whole file and **not one** begins with
`/ch`, `/bus`, `/aux`, `/main`, `/mtx`, `/dca` or `/fx`. A UTF-16LE scan finds
three, all date-format fragments. Unpacking the image was not attempted and is
not recommended as the next move — it is a large effort with an uncertain
result, when two cheaper routes exist.

## The two cheaper routes, in order

1. **Observe a live console.** WING Edit speaks this protocol to the console on
   port 2223. Running it against ToanAZ's WING on a network where the traffic
   can be captured yields the real addresses, in the real dialect, for exactly
   the parameters we care about — and it verifies them at the same time, which
   a document could not. This is the highest-value single hour available to
   sub-project C.
2. **An external protocol reference.** The WING OSC address tree is documented
   outside this repository. Anything obtained that way is a **hypothesis until
   probed against his console**, and should be recorded as such — the same
   standard the rest of this project holds itself to.

Note in favour of route 1: the scene file's own key structure is already known
in full, and it is strongly suggestive. `ae_data.ch.1.send.8.mode` reads like
`/ch/1/send/8/mode`. **That is a resemblance, not a finding.** It is exactly the
kind of plausible mapping that would be assumed, shipped, and discovered to be
wrong on the one address that differs — and the failure would be a wrong
parameter written to a live console during a show. Do not build on it without
observation.

## Reproduction (PowerShell)

From the repository root. `pymupdf` is installed; it is not a project
dependency, so a fresh environment needs `pip install pymupdf` first.

```powershell
python -c "import fitz; d=fitz.open('user-files/User-Manual_WING-series_2025-10-20.pdf'); print(d.page_count); print([i+1 for i,p in enumerate(d) if 'OSC' in p.get_text()])"
```

```powershell
python -c "import fitz; d=fitz.open('user-files/User-Manual_WING-series_2025-10-20.pdf'); print([l for l in d[49].get_text().splitlines() if 'OSC' in l])"
```

Note that `user-files/User-Manual_WING-series_*.pdf` and
`user-files/WING-Edit.exe` are both gitignored, so **neither exists in a git
worktree** — run these from the main checkout. Getting a `FileNotFoundError`
from a worktree is expected and is not evidence the file is missing.

## Do not repeat

- Searching the manual for an OSC address table. There is none; one page of 167
  mentions OSC and it is about locking the port.
- Scanning `WING-Edit.exe` for address strings, ASCII or UTF-16. Both done,
  both empty.
- Searching the PDF for "TCP". The manual writes "TPC".
