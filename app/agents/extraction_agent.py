from dataclasses import dataclass
import re

from app.api.schemas import EvidenceItem, ReviewFlag


@dataclass(frozen=True)
class ClinicalFinding:
    name: str
    category: str
    evidence: EvidenceItem
    context: str
    confidence: float
    flags: tuple[ReviewFlag, ...] = ()


def _redact_snippet(snippet: str) -> str:
    without_names = re.sub(
        r"\b(Patient|Mr\.|Ms\.|Mrs\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
        r"\1 [REDACTED]",
        snippet,
    )
    return without_names.strip()


def _window(text: str, start: int, end: int, radius: int = 28) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return text[left:right].lower()


def _evidence(text: str, start: int, end: int) -> EvidenceItem:
    return EvidenceItem(
        start=start,
        end=end,
        redacted_snippet=_redact_snippet(text[start:end]),
    )


class ClinicalExtractionAgent:
    def extract(self, note_text: str) -> list[ClinicalFinding]:
        findings: list[ClinicalFinding] = []
        lower_note = note_text.lower()

        for match in re.finditer(r"\b(?:essential\s+)?hypertension\b", note_text, re.I):
            context = _window(note_text, match.start(), match.end())
            flags: list[ReviewFlag] = []
            confidence = 0.94 if "essential" in match.group(0).lower() else 0.82
            if "family history" in context:
                flags.append(
                    ReviewFlag(
                        type="family_history",
                        message="Family history is not a current diagnosis.",
                    )
                )
                confidence = 0.35
            elif "history of" in context:
                flags.append(
                    ReviewFlag(
                        type="history_of_condition",
                        message="History-of phrasing needs human review.",
                    )
                )
                confidence = 0.55
            findings.append(
                ClinicalFinding(
                    name="hypertension",
                    category="diagnosis",
                    evidence=_evidence(note_text, match.start(), match.end()),
                    context=context,
                    confidence=confidence,
                    flags=tuple(flags),
                )
            )

        for match in re.finditer(r"\b(?:type\s+2\s+)?diabetes(?:\s+mellitus)?\b", note_text, re.I):
            context = _window(note_text, match.start(), match.end())
            flags = []
            confidence = 0.9 if "type 2" in match.group(0).lower() else 0.62
            if "without complications" not in lower_note and "type 2" not in context:
                flags.append(
                    ReviewFlag(
                        type="specificity_gap",
                        message="Diabetes documentation lacks type or complication specificity.",
                    )
                )
            findings.append(
                ClinicalFinding(
                    name="diabetes",
                    category="diagnosis",
                    evidence=_evidence(note_text, match.start(), match.end()),
                    context=context,
                    confidence=confidence,
                    flags=tuple(flags),
                )
            )

        for match in re.finditer(r"\bpneumonia\b", note_text, re.I):
            context = _window(note_text, match.start(), match.end(), radius=40)
            flags = []
            confidence = 0.84
            if "denies" in context or "no evidence of" in context:
                flags.append(
                    ReviewFlag(
                        type="negated_condition",
                        message="Pneumonia is negated and should not be coded as active.",
                    )
                )
                confidence = 0.2
            if "ruled out" in context or "rule out" in context:
                flags.append(
                    ReviewFlag(
                        type="ruled_out_condition",
                        message="Pneumonia was ruled out and should not be coded as active.",
                    )
                )
                confidence = 0.18
            if "history of" in context:
                flags.append(
                    ReviewFlag(
                        type="history_of_condition",
                        message="History-of phrasing needs human review.",
                    )
                )
                confidence = min(confidence, 0.48)
            findings.append(
                ClinicalFinding(
                    name="pneumonia",
                    category="diagnosis",
                    evidence=_evidence(note_text, match.start(), match.end()),
                    context=context,
                    confidence=confidence,
                    flags=tuple(flags),
                )
            )

        for match in re.finditer(r"\blaparoscopic\s+cholecystectomy\b|\bcholecystectomy\b", note_text, re.I):
            findings.append(
                ClinicalFinding(
                    name="cholecystectomy",
                    category="procedure",
                    evidence=_evidence(note_text, match.start(), match.end()),
                    context=_window(note_text, match.start(), match.end()),
                    confidence=0.96 if "performed" in lower_note else 0.76,
                    flags=(),
                )
            )

        if "invalid-code" in lower_note or "unknown code" in lower_note:
            start = lower_note.find("invalid-code")
            if start < 0:
                start = lower_note.find("unknown code")
            end = start + len("invalid-code")
            findings.append(
                ClinicalFinding(
                    name="invalid-code-simulation",
                    category="diagnosis",
                    evidence=_evidence(note_text, start, min(len(note_text), end)),
                    context=_window(note_text, start, min(len(note_text), end)),
                    confidence=0.4,
                    flags=(
                        ReviewFlag(
                            type="invalid_code_simulation",
                            message="Sample triggers an invalid-code validation path.",
                        ),
                    ),
                )
            )

        return findings
