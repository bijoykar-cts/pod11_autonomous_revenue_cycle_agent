from app.agents.extraction_agent import ClinicalFinding
from app.api.schemas import CodeRecommendation, ReviewFlag
from app.corpus.models import Corpus
from app.corpus.validator import validate_code


class DiagnosisRecommendationAgent:
    def recommend(self, corpus: Corpus, findings: list[ClinicalFinding]) -> list[CodeRecommendation]:
        recommendations: list[CodeRecommendation] = []
        for finding in findings:
            if finding.category != "diagnosis":
                continue

            code = self._code_for_finding(finding)
            validation = validate_code(corpus, code, "ICD-10-CM")
            flags = list(finding.flags)
            status = self._status_for_finding(finding, validation.validation_status)
            validation_score = 1.0 if validation.validation_status == "valid" else 0.0

            if validation.validation_status != "valid":
                flags.append(
                    ReviewFlag(
                        type="invalid_code",
                        message="Candidate code is not present in the configured corpus.",
                    )
                )

            recommendations.append(
                CodeRecommendation(
                    code=code,
                    description=validation.description,
                    code_system="ICD-10-CM",
                    status=status,
                    validation_status=validation.validation_status,
                    confidence=round(min(finding.confidence, validation_score), 2),
                    retrieval_score=round(finding.confidence * 0.94, 2),
                    evidence_score=round(finding.confidence, 2),
                    validation_score=validation_score,
                    evidence=[finding.evidence],
                    review_flags=flags,
                )
            )
        return recommendations

    def _code_for_finding(self, finding: ClinicalFinding) -> str:
        if finding.name == "hypertension":
            return "I10"
        if finding.name == "diabetes":
            return "E11.9" if finding.confidence >= 0.9 else "E11"
        if finding.name == "pneumonia":
            return "J18.9"
        if finding.name == "invalid-code-simulation":
            return "ZZZ999"
        return "ZZZ999"

    def _status_for_finding(self, finding: ClinicalFinding, validation_status: str) -> str:
        flag_types = {flag.type for flag in finding.flags}
        if validation_status != "valid":
            return "rejected"
        if {"negated_condition", "ruled_out_condition", "family_history"} & flag_types:
            return "rejected"
        if "specificity_gap" in flag_types or "history_of_condition" in flag_types:
            return "needs_documentation"
        if finding.confidence >= 0.85:
            return "accepted"
        return "suggested"
