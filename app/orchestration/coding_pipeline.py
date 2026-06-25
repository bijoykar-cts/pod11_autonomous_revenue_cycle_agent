from app.agents.diagnosis_agent import DiagnosisRecommendationAgent
from app.agents.extraction_agent import ClinicalExtractionAgent
from app.agents.procedure_agent import ProcedureRecommendationAgent
from app.api.schemas import CodingData, DebugInfo, ReviewFlag
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
        diagnosis_codes = self._diagnosis_agent.recommend(self._corpus, findings)
        procedure_codes = self._procedure_agent.recommend(self._corpus, findings)
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
