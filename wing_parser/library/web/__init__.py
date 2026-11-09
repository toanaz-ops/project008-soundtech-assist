"""Web side of the mixing knowledge library (single-page app).

Two modes share `static/`: a static export (`export.py`, read-only, data
embedded) and a FastAPI server (`server.py`, PRJ012 auth, optional extra
`library-web`). This package never imports Qt or FastAPI at package level.
"""
