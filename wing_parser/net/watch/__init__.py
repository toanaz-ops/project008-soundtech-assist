"""Watch a running console for changes, by polling.

Deliberately not a subscription: only one OSC subscription exists
console-wide and it expires after 10s (design doc S3.1), so subscribing
would displace WING-Edit, Companion or any other client. Polling
consumes nothing another client can lose.
"""
