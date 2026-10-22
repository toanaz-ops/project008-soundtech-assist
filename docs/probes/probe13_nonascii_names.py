r"""Probe 13: how does the desk encode non-ASCII (Vietnamese) names over OSC?

`net/codec.py` decodes every string as strict ASCII, so a UTF-8 channel name
(or a truncated/stray datagram) raises out of a whole Pull/Discover/Watch.
Whether WING really emits UTF-8 -- or cp1258, or latin-1 -- has never been
measured (audit p008-fable-audit-20261021, finding "One malformed or
non-ASCII datagram aborts an entire Pull"). This probe records the raw bytes.

For each `/ch/N/name` (plus bus, main and dca names) it sends one bare GET,
keeps the RAW reply bytes, prints them in hex, then tries to decode the name
string as ascii, utf-8, cp1258 and latin-1. It never decodes through
`codec.decode`, so a bad datagram cannot crash it: errors are recorded per
address and the run continues.

READ-ONLY. It only sends the bare address GET form built by `codec.encode`.
It imports nothing from `wing_parser.net.write` and never sets, toggles,
pushes or writes anything.

Usage:
    python docs/probes/probe13_nonascii_names.py <host> [--channels 1-40]
                                                  [--out file.json]

Cach chay (how to run):
  1. WING-Edit co the van dang ket noi, khong sao.
  2. Truoc het, trong WING-Edit dat ten mot kenh la "Ca si Duc" (co dau:
     "Ca sĩ Đức"), vi du kenh 1.
  3. Chay lenh (khoang 1 phut, chi doc, khong ghi gi len ban mix):
       python docs\probes\probe13_nonascii_names.py <IP-cua-ban> --out probe13.json
  4. Gui file probe13.json (va doan chu in ra man hinh) lai.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

# The repo root, resolved from this file, so the probe runs from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wing_parser.net.client import OSC_PORT  # noqa: E402
from wing_parser.net.codec import encode  # noqa: E402

ENCODINGS = ("ascii", "utf-8", "cp1258", "latin-1")
DEFAULT_TIMEOUT = 0.5
_RECV_BUFSIZE = 65536

# Families probed besides `ch`, with their slot counts on a full WING.
OTHER_FAMILIES = (("bus", 16), ("main", 4), ("dca", 16))


def parse_range(text: str) -> range:
    """'1-40' -> range(1, 41); '7' -> range(7, 8)."""
    first, _, last = text.partition("-")
    low, high = int(first), int(last or first)
    if low < 1 or high < low:
        raise ValueError(f"bad channel range {text!r}")
    return range(low, high + 1)


def _read_field(data: bytes, offset: int) -> tuple[bytes, int]:
    """One NUL-terminated, 4-byte-padded field, returned as raw bytes."""
    end = data.index(b"\x00", offset)
    return data[offset:end], offset + (end - offset) // 4 * 4 + 4


def extract_name_bytes(data: bytes) -> bytes:
    """Raw bytes of the first string argument of an OSC reply.

    Raises ValueError for anything that is not a well-formed reply with a
    string argument. Deliberately does not decode the bytes.
    """
    if not data:
        raise ValueError("malformed datagram: empty")
    try:
        _address, offset = _read_field(data, 0)
        if data[offset : offset + 1] != b",":
            raise ValueError("no type tag string")
        tags, offset = _read_field(data, offset)
        for tag in tags[1:].decode("ascii"):
            if tag == "s":
                value, _ = _read_field(data, offset)
                return value
            if tag in "fi":
                offset += 4
            else:
                raise ValueError(f"unsupported type tag {tag!r}")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"malformed datagram: {exc}") from exc
    raise ValueError("malformed datagram: no string argument")


def try_decodes(raw: bytes) -> dict[str, str | None]:
    """Decode `raw` with each candidate; None marks a failure."""
    results: dict[str, str | None] = {}
    for encoding in ENCODINGS:
        try:
            results[encoding] = raw.decode(encoding)
        except UnicodeDecodeError:
            results[encoding] = None
    return results


def build_record(address: str, data: bytes | None, error: str | None = None) -> dict:
    """One result row. Never raises: a bad datagram becomes an `error`."""
    record: dict = {"address": address, "datagram_hex": None, "name_hex": None,
                    "decodes": None, "non_ascii": False, "error": error}
    if data is not None:
        record["datagram_hex"] = data.hex()
        try:
            raw = extract_name_bytes(data)
        except ValueError as exc:
            record["error"] = str(exc)
            return record
        record["name_hex"] = raw.hex()
        record["decodes"] = try_decodes(raw)
        record["non_ascii"] = any(byte >= 0x80 for byte in raw)
    return record


def verdict(records: list[dict]) -> str:
    """One-line summary over all records."""
    non_ascii = [r for r in records if r["non_ascii"]]
    answered = sum(1 for r in records if r["name_hex"] is not None)
    errors = sum(1 for r in records if r["error"])
    if not non_ascii:
        return (f"non-ASCII seen: no; consistent with: n/a "
                f"({answered} names read, {errors} errors/silent)")
    consistent = [enc for enc in ENCODINGS[1:]
                  if all(r["decodes"][enc] is not None for r in non_ascii)]
    shown = ", ".join(consistent) if consistent else "none of utf-8/cp1258/latin-1"
    return (f"non-ASCII seen: yes ({len(non_ascii)} names); "
            f"consistent with: {shown} ({errors} errors/silent)")


def targets(channels: range) -> list[str]:
    addresses = [f"/ch/{n}/name" for n in channels]
    for family, count in OTHER_FAMILIES:
        addresses += [f"/{family}/{n}/name" for n in range(1, count + 1)]
    return addresses


def probe_address(sock: socket.socket, host: str, port: int, address: str) -> dict:
    """One bare GET and one bounded receive; every failure becomes a record."""
    try:
        sock.sendto(encode(address), (host, port))
        data, _ = sock.recvfrom(_RECV_BUFSIZE)
    except socket.timeout:
        return build_record(address, None, "no reply (timeout)")
    except OSError as exc:
        return build_record(address, None, f"socket error: {exc}")
    return build_record(address, data)


def print_record(record: dict) -> None:
    print(f"{record['address']:18s} ", end="")
    if record["name_hex"] is None:
        raw = f"  raw={record['datagram_hex']}" if record["datagram_hex"] else ""
        print(f"-- {record['error']}{raw}")
        return
    marks = " ".join(f"{enc}={'OK' if text is not None else 'fail'}"
                     for enc, text in record["decodes"].items())
    print(f"hex={record['name_hex'] or '(empty)'}  {marks}"
          + ("  <NON-ASCII>" if record["non_ascii"] else ""))
    if record["non_ascii"]:
        for enc, text in record["decodes"].items():
            if text is not None:
                print(f"{'':18s}   {enc}: {text!r}")


def run(host: str, channels: range, timeout: float = DEFAULT_TIMEOUT,
        port: int = OSC_PORT) -> list[dict]:
    records: list[dict] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        for address in targets(channels):
            record = probe_address(sock, host, port, address)
            records.append(record)
            print_record(record)
    finally:
        sock.close()
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only probe of non-ASCII name encoding.")
    parser.add_argument("host")
    parser.add_argument("--channels", default="1-40")
    parser.add_argument("--out")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)

    print(f"probe 13 -- non-ASCII name encoding, read-only, against {args.host}\n")
    records = run(args.host, parse_range(args.channels), args.timeout)
    line = verdict(records)
    print(f"\nVERDICT: {line}")
    if args.out:
        Path(args.out).write_text(
            json.dumps({"host": args.host, "verdict": line, "records": records},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
