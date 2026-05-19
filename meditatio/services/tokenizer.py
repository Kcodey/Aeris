from typing import Dict, Any, List
import json

import httpx


class Tokenizer:
    """Token usage estimation with multiple fallback strategies."""

    def __init__(self, provider_manager=None):
        self.provider_manager = provider_manager
        self._cache: Dict[str, Any] = {}

    async def estimate_tokens(
        self,
        messages: List[Dict[str, Any]],
        provider_name: str = "default",
    ) -> int:
        """
        Estimate token count for messages.

        Priority:
        1. Provider's /tokenize endpoint (if SGLang)
        2. Model-specific tokenizer
        3. tiktoken (cl100k_base)
        4. Character count / 4
        """
        text = json.dumps(messages)

        # Priority 1: Provider tokenize endpoint
        if self.provider_manager:
            try:
                provider = self.provider_manager.get_provider(provider_name)
                if hasattr(provider, "count_tokens"):
                    return await provider.count_tokens(text)
            except Exception:
                pass

        # Priority 2: tiktoken
        try:
            import tiktoken
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            pass

        # Priority 3: Rough estimation
        return len(text) // 4

    async def estimate_output_tokens(self, text: str) -> int:
        """Estimate token count for output text."""
        # Same priority as above, but for single text
        try:
            import tiktoken
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            return len(text) // 4


# Global tokenizer instance
_tokenizer: Tokenizer = None


def get_tokenizer() -> Tokenizer:
    """Get or create tokenizer singleton."""
    global _tokenizer
    if _tokenizer is None:
        from meditatio.services.provider_manager import get_provider_manager
        _tokenizer = Tokenizer(get_provider_manager())
    return _tokenizer
