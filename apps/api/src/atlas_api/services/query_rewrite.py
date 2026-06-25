from atlas_api.query_rewrite_providers.base import QueryRewriteProvider


class QueryRewriteService:
    def __init__(self, provider: QueryRewriteProvider, max_rewrites: int = 3) -> None:
        self._provider = provider
        self._max_rewrites = max_rewrites

    def rewrite(self, query: str) -> list[str]:
        queries = [query]
        for rewrite in self._provider.rewrite(query)[: self._max_rewrites]:
            if rewrite and rewrite not in queries:
                queries.append(rewrite)

        return queries
