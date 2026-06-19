from atlas_api.ai_providers.base import AIProvider


class LocalAIProvider(AIProvider):
    def generate_answer(self, question: str, context: list[str]) -> str:
        if not context:
            return f"Atlas does not have enough context yet to answer: {question}"

        joined_context = " ".join(context)
        return f"Based on the current Atlas notes: {joined_context}"

