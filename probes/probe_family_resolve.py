# Probe: do the top-level families answer on this console right now?
from wing_parser.net.client import WingClient

HOST = "192.168.128.28"
c = WingClient(HOST)
for addr in ["/", "/ch", "/aux", "/bus", "/main", "/mtx", "/io", "/dca", "/$ctl"]:
    try:
        r = c.request(addr)
        print(repr(addr), "->", r)
    except Exception as e:
        print(repr(addr), "-> ERROR:", type(e).__name__, e)
