from app.corpus.models import Corpus, CorpusRecord


class LocalRetriever:
    def __init__(self, corpus: Corpus) -> None:
        self._corpus = corpus

    def search(self, query: str, code_system: str | None = None) -> list[CorpusRecord]:
        terms = {term.lower() for term in query.split() if len(term) > 2}
        matches: list[CorpusRecord] = []
        for record in self._corpus.records.values():
            if code_system is not None and record.code_system != code_system:
                continue
            haystack = f"{record.code} {record.description}".lower()
            if any(term in haystack for term in terms):
                matches.append(record)
        return matches
