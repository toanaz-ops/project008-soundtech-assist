"""Probe 7: why did discovery report /main absent when probe 3 read it fine?

Probe 3 read /main/1/$fdr and got sff ('-oo', 0.0, -144.0).
Probe 6's discovery asked the same address and got None.

Both cannot be right. The suspicion is ORDER: in probe 6 the /main query was
the first request after /bus/17 timed out, and a socket that has just eaten a
2s timeout may not be in the state the next request assumes. If that is the
cause, it is a real design constraint for the watch-list builder, not a curio.

Four tests, each read-only:
  A. /main/1/$fdr on a brand-new socket, alone
  B. the same address ten times in a row, same socket
  C. the same address immediately after a deliberate timeout on a dead address
  D. how many /main slots answer, counted on a fresh socket each time

Run:  python probe7_main.py 192.168.128.28
"""

from __future__ import annotations

import sys

sys.path.insert(0, r"Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND\.claude\worktrees\project-capabilities-next-steps-8ec61c")

from wing_parser.net.client import WingClient  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"

TARGET = "/main/1/$fdr"
DEAD = "/bus/17/$fdr"          # probe 6 showed bus stops at 16
SHORT_TIMEOUT = 0.4            # keep test C quick; a dead address never answers


def show(label: str, reply) -> None:
    if reply is None:
        print(f"  {label:52s} SILENT")
    else:
        print(f"  {label:52s} {reply.typetag} {reply.args!r}")


def main() -> None:
    print(f"probe 7 -- the /main contradiction, against {HOST}\n")

    print("A. fresh socket, single read")
    with WingClient(HOST) as client:
        show(TARGET, client.request(TARGET))

    print("\nB. ten reads in a row on one socket")
    with WingClient(HOST) as client:
        silent = 0
        for index in range(10):
            reply = client.request(TARGET)
            if reply is None:
                silent += 1
                print(f"  read {index + 1}: SILENT")
        print(f"  {10 - silent}/10 answered")

    print(f"\nC. read {TARGET} immediately after a timeout on {DEAD}")
    with WingClient(HOST, timeout=SHORT_TIMEOUT) as client:
        show(f"{DEAD} (expected silent)", client.request(DEAD))
        show(f"{TARGET} straight after", client.request(TARGET))
        show(f"{TARGET} again", client.request(TARGET))

    print("\nD. how many /main slots exist? fresh socket per probe")
    present = []
    for index in range(1, 9):
        with WingClient(HOST, timeout=SHORT_TIMEOUT) as client:
            if client.request(f"/main/{index}/$fdr") is not None:
                present.append(index)
    print(f"  /main slots answering: {present}")


if __name__ == "__main__":
    main()
