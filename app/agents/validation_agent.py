from app.api.schemas import CodeRecommendation
from app.corpus.models import Corpus
from app.corpus.validator import validate_code


class ValidationAgent:
    def validate(self, corpus: Corpus, recommendations: list[CodeRecommendation]) -> list[CodeRecommendation]:
        validated: list[CodeRecommendation] = []
        for recommendation in recommendations:
            result = validate_code(corpus, recommendation.code, recommendation.code_system)
            if result.validation_status == recommendation.validation_status:
                validated.append(recommendation)
                continue
            validated.append(
                recommendation.model_copy(
                    update={
                        "description": result.description,
                        "validation_status": result.validation_status,
                        "validation_score": 1.0 if result.validation_status == "valid" else 0.0,
                    }
                )
            )
        return validated
