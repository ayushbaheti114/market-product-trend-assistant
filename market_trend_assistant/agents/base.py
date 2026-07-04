"""
agents/base.py
--------------
Common base class for all agents. Provides consistent logging and an
optional hook into the Claude API for agents that want LLM-assisted
extraction when config.USE_LLM is True.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class BaseAgent:
    name = "base_agent"

    def log(self, message: str):
        print(f"[{self.name}] {message}")

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Optional Claude API call. Requires ANTHROPIC_API_KEY in env.
        Falls back gracefully -- callers should always have a rule-based
        path since this is not guaranteed to run (see config.USE_LLM)."""
        if not config.USE_LLM:
            raise RuntimeError("LLM disabled: set ANTHROPIC_API_KEY to enable.")
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed.")

        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )

    def run(self, *args, **kwargs):
        raise NotImplementedError
