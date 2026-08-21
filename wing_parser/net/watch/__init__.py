"""Watch a running console for changes, by polling.

Deliberately not a subscription: only one OSC subscription exists
console-wide and it expires after 10s (design doc S3.1), so subscribing
would displace whatever holds that slot -- WING-Edit, Companion or any
other client (whether WING-Edit itself uses the OSC subscription at all
is unmeasured -- design doc S2.6(3)). Polling consumes no shared
resource, so it cannot displace another client.
"""
