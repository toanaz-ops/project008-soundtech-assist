"""WING-over-Ethernet subsystem: talk to a running console over OSC."""

from __future__ import annotations

from wing_parser.net.codec import OscMessage, decode, encode, leaf_value

__all__ = ["OscMessage", "decode", "encode", "leaf_value"]
