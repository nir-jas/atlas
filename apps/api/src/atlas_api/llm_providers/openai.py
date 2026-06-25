from typing import Any

from atlas_api.llm_providers.base import LLMProviderError


class OpenAILLMProvider:
    provider = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.4",
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        self.model = model
        self._client = client or self._build_client(api_key)

    @staticmethod
    def _build_client(api_key: str) -> Any:
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                "The OpenAI SDK is not installed. Run `uv sync --extra dev`."
            ) from error
        return OpenAI(api_key=api_key)

    def generate_answer(self, *, query: str, context: str) -> str:
        try:
            response = self._client.responses.create(
                model=self.model,
                instructions=(
                    "Answer the user question using only the supplied context. "
                    "If the context does not support an answer, say so. "
                    "Do not include citations in the answer text."
                ),
                input=f"Question:\n{query}\n\nContext:\n{context}",
                store=False,
            )
        except Exception as error:
            raise LLMProviderError("OpenAI answer generation failed") from error

        answer = response.output_text
        if not isinstance(answer, str) or not answer.strip():
            raise LLMProviderError("OpenAI returned an empty answer")
        return answer.strip()
