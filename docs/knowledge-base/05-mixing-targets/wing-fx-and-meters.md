# WING FX slots, automix group and meters

Sources: R7 (Drew Brashler, WING specialist blog), `maillot` (WING Remote Protocols V3.0.5-1 text extract),
the scene files in `user-files/`. The official WING manual and Effects Guide were **not read**.

## FX slots and roles

- 16 FX slots; reverbs and delays are said to live in slots 1-8 only (blog-level, unverified).
- A slot is used by inserting it on a bus: `bus.N.preins` or `postins` with `ins = "FXk"`. Automix finds FX
  buses by **what is inserted**, not by bus name (AM-13): PLATE -> vocal plate, ROOM -> short room, HALL and
  CONCERT -> long hall, ST-DL -> delay.
- Changing `fx.k.mdl` does not create the new model's parameter keys, so loading a model into an empty slot is
  not something a patch can do (AM-14). Automix writes only existing keys and otherwise shows a Suggestion.
- Blue Plate ranges quoted by R7: pre-delay 0-200 ms, decay 0.2-5 s, damping 2-20 kHz, low cut 20-400 Hz, high
  cut 2-20 kHz. Other models' ranges are unverified; automix clamps to the ranges above.

## Automix group (speech)

Per Maillot, WING has two gain-sharing groups X and Y (up to 16 inputs). A channel joins through
`postins.mode = AUTO_X|AUTO_Y`, with `postins.on` and weight `postins.w` (-12..+12). The algorithm and the
weight unit are undocumented. Automix v1 puts speech channels with a free post-insert into group X (AM-16),
weight 0 and +4 for the MC (matches Doctor PC7), and skips channels whose gate is on (Doctor E6).

## Meters (experimental, phase 2, off by default)

Meters are **not** available over OSC; only the native protocol channel 3 offers them (Maillot pp.86-87).
Request: declare a UDP port, ask for a family of channels, renew at most every 5 s. Reply: 4-byte id then
int16 big-endian values, dB = v/256, 0x8000 = no signal. Channel stride 8 (in L/R, out L/R, gate key, gate
gain, dyn key, dyn gain) in the V1 layout. **Unverified:** request transport (TCP or UDP 2222), the V2 stride
and table (garbled in the extract), pre/post-fader tap, index base. Only one OSC event subscription exists at
a time (last requester wins), which can collide with Companion or WING-Edit. Acceptance belongs to HW-192.
