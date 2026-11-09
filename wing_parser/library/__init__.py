"""The mixing knowledge library: store, validation, history, search (no Qt).

Format: knowledge/library/SCHEMA.md. Entries are written only through
`LibraryStore` so every change is validated and logged.
"""

from wing_parser.library.schema import load_publishers, load_topics
from wing_parser.library.search import facets, search
from wing_parser.library.store import (
    EntryExists,
    LibraryStore,
    LoadedEntry,
    RevisionConflict,
    Revision,
    ValidationFailed,
    default_author,
    dump_entry,
)
from wing_parser.library.validate import Issue, errors, validate
from wing_parser.showcontext.ingest.keywords import fold

__all__ = [
    "EntryExists", "Issue", "LibraryStore", "LoadedEntry", "Revision", "RevisionConflict",
    "ValidationFailed", "default_author", "dump_entry", "errors", "facets",
    "fold", "load_publishers", "load_topics", "search", "validate",
]
