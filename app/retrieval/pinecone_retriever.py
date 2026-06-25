class PineconeRetriever:
    """Optional integration boundary for post-MVP Pinecone retrieval."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def available(self) -> bool:
        return self.enabled
