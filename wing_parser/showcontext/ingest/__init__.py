"""Assisted ingest: a producer's running order becomes a show context.

Four modules, one direction: sheet -> mapping -> build -> emit. Nothing
here calls a model; the half that does lives in G2b.
"""
