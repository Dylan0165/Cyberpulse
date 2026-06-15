"""Multi-AI provider abstraction.

Three providers behind one OpenAI-compatible interface:
  - deepseek  (default, included)
  - anthropic (Claude, paid upgrade) — via Anthropic's OpenAI-compatible endpoint
  - runpod    ("Scanix AI", EU-only self-hosted, paid upgrade)

A user only routes to a non-default provider when ai_provider_active is True.
On any failure the provider falls back to DeepSeek automatically.
Provider API keys live in env vars (platform-held), never per request body.
"""

import logging
import os

logger = logging.getLogger(__name__)


class AIProvider:
    def __init__(self, user=None):
        self.provider = "deepseek"
        if user is not None and getattr(user, "ai_provider_active", False):
            self.provider = getattr(user, "ai_provider", None) or "deepseek"
        if self.provider not in ("deepseek", "anthropic", "runpod"):
            self.provider = "deepseek"

    # ── Client builders ───────────────────────────────────────────────────────

    def get_client_and_model(self):
        if self.provider == "anthropic":
            return self._anthropic_client()
        if self.provider == "runpod":
            return self._runpod_client()
        return self._deepseek_client()

    def _deepseek_client(self):
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY", "no-key"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        return client, os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def _anthropic_client(self):
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("ANTHROPIC_API_KEY", "no-key"),
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
        )
        return client, os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def _runpod_client(self):
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("RUNPOD_API_KEY", "no-key"),
            base_url=os.getenv("RUNPOD_ENDPOINT_URL", "http://localhost:8000/v1"),
        )
        return client, os.getenv("RUNPOD_MODEL_NAME", "mistral-7b-instruct")

    # ── Convenience one-shot analyze (used by M13/M15) ────────────────────────

    def analyze(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        client, model = self.get_client_and_model()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                timeout=60,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            logger.error("AI provider %s failed: %s — falling back to deepseek", self.provider, exc)
            if self.provider != "deepseek":
                self.provider = "deepseek"
                return self.analyze(system_prompt, user_prompt, max_tokens)
            raise
