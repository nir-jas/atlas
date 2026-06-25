from dataclasses import dataclass

from atlas_api.schemas.rag import SearchResult


@dataclass(frozen=True)
class AssembledContext:
    retrieved_chunks: list[SearchResult]
    text: str


class ContextAssemblyService:
    """Format ranked retrieval results into inspectable prompt context."""

    def assemble(
        self,
        query: str,
        retrieved_chunks: list[SearchResult],
        *,
        max_chunks: int | None = None,
        similarity_score_threshold: float | None = None,
        max_characters: int | None = None,
    ) -> AssembledContext:
        """Filter ranked chunks and preserve their order in the final context.

        The query is part of the assembly contract even though this milestone
        does not add instructions or an LLM prompt around the assembled text.
        """
        _ = query
        selected_chunks = retrieved_chunks
        if similarity_score_threshold is not None:
            selected_chunks = [
                chunk
                for chunk in selected_chunks
                if chunk.similarity_score is None
                or chunk.similarity_score >= similarity_score_threshold
            ]
        if max_chunks is not None:
            selected_chunks = selected_chunks[:max_chunks]

        formatted_chunks: list[str] = []
        budgeted_chunks: list[SearchResult] = []
        context_length = 0
        for chunk in selected_chunks:
            formatted_chunk = self._format_chunk(chunk)
            separator_length = len("\n\n---\n\n") if formatted_chunks else 0
            candidate_length = context_length + separator_length + len(formatted_chunk)
            if max_characters is not None and candidate_length > max_characters:
                break
            formatted_chunks.append(formatted_chunk)
            budgeted_chunks.append(chunk)
            context_length = candidate_length

        return AssembledContext(
            retrieved_chunks=budgeted_chunks,
            text="\n\n---\n\n".join(formatted_chunks),
        )

    @staticmethod
    def _format_chunk(chunk: SearchResult) -> str:
        section = chunk.section or "Unspecified"
        return f"Source: {chunk.source_name}\nSection: {section}\n\n{chunk.text}"
