from typing import List, Dict, Any


class FeedbackSummarizer:
    """Summarize external feedback items into a short natural-language suggestion.

    This class is a thin wrapper; it expects an `llm_provider`-like object with
    a `_request(prompt, system_prompt=...)` method that returns a string.
    """

    def __init__(self, llm_provider):
        self.llm = llm_provider

    def summarize(self, items: List[Dict[str, Any]]) -> str:
        if not items:
            return "No external context found."

        # build a compact prompt: include up to 5 items
        snippets = []
        for i, it in enumerate(items[:5], start=1):
            if isinstance(it, dict):
                content = it.get("content") or str(it)
            else:
                content = str(it)
            snippets.append(f"[{i}] {content}")

        prompt = (
            "You are a concise financial assistant. Given the following context items, "
            "provide a short (2-4 sentences) actionable summary and any recommendations for gaps or follow-ups.\n\n"
            "Context:\n"
            + "\n".join(snippets)
        )

        try:
            out = self.llm._request(prompt, system_prompt="You are a helpful financial analyst.")
            return out.strip()
        except Exception:
            # best-effort fallback: join raw snippets
            return "; ".join(snippets)
