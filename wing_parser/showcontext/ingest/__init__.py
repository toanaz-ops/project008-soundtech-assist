"""Assisted ingest: a producer's running order becomes a show context.

Five modules, one direction: sheet -> mapping -> build -> propose ->
emit (design spec section 8). Nothing here calls a model; the half that
does lives in G2b.
"""
