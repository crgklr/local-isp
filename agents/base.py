"""Base agent class for the content pipeline."""

from __future__ import annotations

import json
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS


client = Anthropic(api_key=ANTHROPIC_API_KEY)


class Agent:
    """Base class for all pipeline agents."""

    name: str = "BaseAgent"
    system_prompt: str = ""
    model: str = MODEL
    max_tokens: int = MAX_TOKENS

    def run(self, user_message: str) -> str:
        """Execute the agent with the given input and return its response."""
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def run_with_prefill(self, user_message: str, prefill: str) -> str:
        """Execute with an assistant prefill to guide output format."""
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": prefill},
            ],
        )
        return prefill + response.content[0].text

    def run_json(self, user_message: str) -> dict:
        """Execute and parse JSON response."""
        raw = self.run_with_prefill(user_message, "{")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
            raise
