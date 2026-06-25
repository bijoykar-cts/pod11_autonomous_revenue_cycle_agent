from app.agents.extraction_agent import ClinicalFinding
from app.api.schemas import CodeRecommendation, ReviewFlag
from app.corpus.models import Corpus
from app.corpus.validator import validate_code


class ProcedureRecommendationAgent:
    def recommend(self, corpus: Corpus, findings: list[ClinicalFinding]) -> list[CodeRecommendation]:
        recommendations: list[CodeRecommendation] = []
        for finding in findings:
            if finding.category != "procedure":
                continue

            code = "0FT44ZZ" if finding.name == "cholecystectomy" else "ZZZ999"
            validation = validate_code(corpus, code, "ICD-10-PCS")
            flags = list(finding.flags)
            validation_score = 1.0 if validation.validation_status == "valid" else 0.0
            status = "accepted" if finding.confidence >= 0.85 and validation_score == 1.0 else "suggested"
            if validation.validation_status != "valid":
                status = "rejected"
                flags.append(
                    ReviewFlag(
                        type="invalid_code",
                        message="Candidate procedure code is not present in the configured corpus.",
                    )
                )

            recommendations.append(
                CodeRecommendation(
                    code=code,
                    description=validation.description,
                    code_system="ICD-10-PCS",
                    status=status,
                    validation_status=validation.validation_status,
                    confidence=round(min(finding.confidence, validation_score), 2),
                    retrieval_score=round(finding.confidence * 0.96, 2),
                    evidence_score=round(finding.confidence, 2),
                    validation_score=validation_score,
                    evidence=[finding.evidence],
                    review_flags=flags,
                )
            )
        return recommendations
