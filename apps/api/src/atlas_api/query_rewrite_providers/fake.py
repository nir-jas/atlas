class FakeQueryRewriteProvider:
    """Deterministic query rewrite provider used for local development and tests."""

    provider = "fake"
    model = "fake-query-rewrite-v1"

    def rewrite(self, query: str) -> list[str]:
        normalized = " ".join(query.split())
        if not normalized:
            return []

        return [
            f"{normalized} context",
            f"{normalized} source details",
        ]
