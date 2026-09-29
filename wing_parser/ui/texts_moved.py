"""English strings that used to be literals inside UI modules.

Found by the bilingual review (2026-09-29): verdict buttons, the detail
panel's box titles, the findings table's headers and count line, and the
import sample pane. A page that builds them reads them at use time, so
the language chosen at start-up reaches them.
"""

MOVED_TEXTS: dict[str, str] = {
    "verdict.correct": "Correct",
    "verdict.false_positive": "False positive",
    "verdict.irrelevant": "Irrelevant",
    "verdict.none_yet": "{rule}: no verdict recorded yet",
    "detail.none_recorded": "none recorded",
    "detail.why": "Why this rule exists",
    "detail.source": "Source",
    "detail.evidence": "Evidence",
    "findings.col.severity": "Severity",
    "findings.col.rule": "Rule",
    "findings.col.target": "Target",
    "findings.col.message": "Message",
    "findings.col.layer": "Layer",
    "findings.count_all": "{total} findings",
    "findings.count_some": "{shown} of {total} findings",
    "import.sample_sheet": "SHEET {name}",
    # Display-only names for raw tokens (`token_labels.label`): the token
    # itself stays the combo's itemData / the model's data.
    "import.step.separator": "›",
    "token.all": "all",
    "token.severity.error": "error",
    "token.severity.warning": "warning",
    "token.severity.info": "info",
    "token.layer.base": "base",
    "token.layer.toanaz": "toanaz",
    "token.layer.show": "show",
    "token.muted.yes": "Yes",
    "token.muted.no": "No",
    "token.match.exact": "exact",
    "token.match.word": "word",
    "token.origin.default": "default",
    "token.origin.manual": "manual",
    "token.origin.default_edited": "default, edited",
}
