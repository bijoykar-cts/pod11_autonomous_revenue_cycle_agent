from app.agents.diagnosis_agent import DiagnosisRecommendationAgent
from app.agents.extraction_agent import ClinicalExtractionAgent
from app.agents.procedure_agent import ProcedureRecommendationAgent
from app.api.schemas import CodeRecommendation, CodingData, DebugInfo, ReviewFlag
from app.corpus.models import Corpus
from app.orchestration.trace import TraceTimer


class CodingPipeline:
    def __init__(self, corpus: Corpus, debug_enabled: bool = False) -> None:
        self._corpus = corpus
        self._debug_enabled = debug_enabled
        self._extractor = ClinicalExtractionAgent()
        self._diagnosis_agent = DiagnosisRecommendationAgent()
        self._procedure_agent = ProcedureRecommendationAgent()

    def run(
        self,
        case_id: str,
        note_text: str,
        include_debug: bool,
        persist_note: bool,
    ) -> CodingData:
        del persist_note
        timer = TraceTimer()
        findings = self._extractor.extract(note_text)
        diagnosis_codes = self._deduplicate_recommendations(
            self._diagnosis_agent.recommend(self._corpus, findings)
        )
        procedure_codes = self._deduplicate_recommendations(
            self._procedure_agent.recommend(self._corpus, findings)
        )
        review_flags = self._collect_review_flags(diagnosis_codes, procedure_codes)
        diagnosis_codes, procedure_codes, conflict_flags = self._resolve_conflicts(
            diagnosis_codes, procedure_codes
        )
        review_flags.extend(conflict_flags)
        trace = timer.finish()

        return CodingData(
            case_id=case_id,
            corpus_version=self._corpus.version,
            diagnosis_codes=diagnosis_codes,
            procedure_codes=procedure_codes,
            review_flags=review_flags,
            debug=(
                DebugInfo(trace_id=trace.trace_id, timing_ms=trace.timing_ms)
                if include_debug and self._debug_enabled
                else None
            ),
        )

    def _collect_review_flags(self, diagnosis_codes, procedure_codes) -> list[ReviewFlag]:
        flags: list[ReviewFlag] = []
        seen: set[tuple[str, str]] = set()
        for recommendation in [*diagnosis_codes, *procedure_codes]:
            for flag in recommendation.review_flags:
                key = (flag.type, flag.message)
                if key not in seen:
                    flags.append(flag)
                    seen.add(key)
            if recommendation.validation_status == "not_in_configured_corpus":
                flag = ReviewFlag(
                    type="invalid_code",
                    message=f"{recommendation.code} is not in the configured corpus.",
                )
                key = (flag.type, flag.message)
                if key not in seen:
                    flags.append(flag)
                    seen.add(key)
            if recommendation.status == "suggested" and recommendation.confidence < 0.6:
                flag = ReviewFlag(
                    type="low_confidence",
                    message=f"{recommendation.code} needs review due to low confidence.",
                )
                key = (flag.type, flag.message)
                if key not in seen:
                    flags.append(flag)
                    seen.add(key)
        return flags

    def _deduplicate_recommendations(
        self, recommendations: list[CodeRecommendation]
    ) -> list[CodeRecommendation]:
        merged_by_key: dict[tuple[str, str], CodeRecommendation] = {}
        order: list[tuple[str, str]] = []
        for recommendation in recommendations:
            key = (recommendation.code, recommendation.code_system)
            if key not in merged_by_key:
                merged_by_key[key] = recommendation
                order.append(key)
                continue
            merged_by_key[key] = self._merge_recommendations(
                merged_by_key[key], recommendation
            )
        return [merged_by_key[key] for key in order]

    def _merge_recommendations(
        self,
        existing: CodeRecommendation,
        incoming: CodeRecommendation,
    ) -> CodeRecommendation:
        evidence = self._unique_evidence([*existing.evidence, *incoming.evidence])
        review_flags = self._unique_review_flags(
            [*existing.review_flags, *incoming.review_flags]
        )
        if existing.status != incoming.status:
            review_flags = self._unique_review_flags(
                [
                    *review_flags,
                    ReviewFlag(
                        type="duplicate_status_conflict",
                        message=(
                            f"Multiple evidence spans produced different statuses for "
                            f"{existing.code}."
                        ),
                    ),
                ]
            )

        return existing.model_copy(
            update={
                "status": self._merge_status(existing.status, incoming.status),
                "confidence": max(existing.confidence, incoming.confidence),
                "retrieval_score": max(existing.retrieval_score, incoming.retrieval_score),
                "evidence_score": max(existing.evidence_score, incoming.evidence_score),
                "validation_score": max(existing.validation_score, incoming.validation_score),
                "evidence": evidence,
                "review_flags": review_flags,
            }
        )

    def _unique_evidence(self, evidence):
        unique = []
        seen: set[tuple[int, int, str]] = set()
        for item in evidence:
            key = (item.start, item.end, item.redacted_snippet)
            if key not in seen:
                unique.append(item)
                seen.add(key)
        return unique

    def _unique_review_flags(self, review_flags: list[ReviewFlag]) -> list[ReviewFlag]:
        unique: list[ReviewFlag] = []
        seen: set[tuple[str, str]] = set()
        for flag in review_flags:
            key = (flag.type, flag.message)
            if key not in seen:
                unique.append(flag)
                seen.add(key)
        return unique

    def _merge_status(self, existing_status: str, incoming_status: str) -> str:
        statuses = {existing_status, incoming_status}
        if len(statuses) == 1:
            return existing_status
        if "needs_documentation" in statuses or "rejected" in statuses:
            return "needs_documentation"
        if "accepted" in statuses:
            return "accepted"
        return "suggested"

    def _resolve_conflicts(self, diagnosis_codes, procedure_codes):
        accepted_diagnoses = [code for code in diagnosis_codes if code.status == "accepted"]
        accepted_procedures = [code for code in procedure_codes if code.status == "accepted"]
        if not accepted_diagnoses or not accepted_procedures:
            return diagnosis_codes, procedure_codes, []

        best_diagnosis = max(accepted_diagnoses, key=lambda code: code.confidence)
        best_procedure = max(accepted_procedures, key=lambda code: code.confidence)
        if best_diagnosis.confidence >= best_procedure.confidence:
            suppressed = [
                code.model_copy(
                    update={
                        "status": "suggested",
                        "review_flags": [
                            *code.review_flags,
                            ReviewFlag(
                                type="conflict_suppressed",
                                message="Procedure candidate suppressed by higher-confidence diagnosis context.",
                            ),
                        ],
                    }
                )
                if code.status == "accepted"
                else code
                for code in procedure_codes
            ]
            return diagnosis_codes, suppressed, [
                ReviewFlag(
                    type="conflict_suppressed",
                    message="Lower-confidence procedure recommendation was suppressed.",
                )
            ]

        suppressed = [
            code.model_copy(
                update={
                    "status": "suggested",
                    "review_flags": [
                        *code.review_flags,
                        ReviewFlag(
                            type="conflict_suppressed",
                            message="Diagnosis candidate suppressed by higher-confidence procedure context.",
                        ),
                    ],
                }
            )
            if code.status == "accepted"
            else code
            for code in diagnosis_codes
        ]
        return suppressed, procedure_codes, [
            ReviewFlag(
                type="conflict_suppressed",
                message="Lower-confidence diagnosis recommendation was suppressed.",
            )
        ]
