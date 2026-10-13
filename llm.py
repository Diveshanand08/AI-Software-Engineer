"""
services/llm.py & llm.py
Multi-provider LLM abstraction layer supporting local Ollama, Groq (Llama 3.3), and Google Gemini.
Handles both full generation and streaming with standardized error handling.
"""

from openai import OpenAI
from core.config import settings
from core.exceptions import ProviderUnavailableError

PROVIDERS = {
    "ollama": {
        "label": "Local (phi3)",
        "model": settings.DEFAULT_OLLAMA_MODEL,
    },
    "groq": {
        "label": "Groq (Llama 3.3 70B)",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "key": lambda: settings.GROQ_API_KEY,
        "key_name": "GROQ_API_KEY",
    },
    "gemini": {
        "label": "Google Gemini Flash",
        "model": "models/gemini-flash-lite-latest",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key": lambda: settings.GEMINI_API_KEY,
        "key_name": "GEMINI_API_KEY",
    },
}


def available_providers() -> list[dict]:
    """Returns list of active providers. Cloud providers appear only if API keys are set."""
    out = []
    for pid, cfg in PROVIDERS.items():
        if pid == "ollama":
            out.append({"id": pid, "label": cfg["label"]})
        elif "key" in cfg and cfg["key"]():
            out.append({"id": pid, "label": cfg["label"]})
    return out


def _get_cfg(provider: str) -> dict:
    cfg = PROVIDERS.get(provider.lower())
    if cfg is None:
        raise ProviderUnavailableError(provider, f"Unknown provider '{provider}'")
    return cfg


def _hosted_client(cfg: dict) -> OpenAI:
    api_key = cfg["key"]()
    if not api_key:
        raise ProviderUnavailableError(
            cfg.get("key_name", "API Key"),
            f"Environment variable '{cfg.get('key_name')}' is missing or empty.",
        )
    return OpenAI(api_key=api_key, base_url=cfg["base_url"])


def generate(messages: list[dict], provider: str = "ollama", ollama_model: str | None = None) -> str:
    """Generate a complete text completion using the specified provider."""
    cfg = _get_cfg(provider)

    if provider == "ollama":
        try:
            import ollama
            res = ollama.chat(
                model=ollama_model or cfg["model"],
                messages=messages,
                options={"num_predict": 600, "num_ctx": 2048, "temperature": 0.2},
                keep_alive="30m",
            )
            return res["message"]["content"]
        except Exception as e:
            import os
            gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
            if gemini_key:
                print(f"[llm] Ollama connection unavailable ({e}), automatically falling back to Gemini...")
                return generate(messages, provider="gemini")
            raise ProviderUnavailableError("ollama", str(e))

    client = _hosted_client(cfg)
    import time
    for attempt in range(3):
        try:
            res = client.chat.completions.create(
                model=cfg["model"], messages=messages, max_tokens=2500, temperature=0.2
            )
            return res.choices[0].message.content or ""
        except Exception as e:
            if ("503" in str(e) or "429" in str(e)) and attempt < 2:
                time.sleep((attempt + 1) * 2)
                continue
            raise ProviderUnavailableError(provider, str(e))


def generate_stream(messages: list[dict], provider: str = "ollama", ollama_model: str | None = None):
    """Yield token chunks sequentially from the selected provider."""
    cfg = _get_cfg(provider)

    if provider == "ollama":
        try:
            import ollama
            stream = ollama.chat(
                model=ollama_model or cfg["model"],
                messages=messages,
                options={"num_predict": 600, "num_ctx": 2048, "temperature": 0.2},
                keep_alive="30m",
                stream=True,
            )
            for part in stream:
                yield part["message"]["content"]
            return
        except Exception as e:
            import os
            gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
            if gemini_key:
                print(f"[llm] Ollama stream unavailable ({e}), automatically falling back to Gemini...")
                for part in generate_stream(messages, provider="gemini"):
                    yield part
                return
            raise ProviderUnavailableError("ollama", str(e))

    client = _hosted_client(cfg)
    try:
        stream = client.chat.completions.create(
            model=cfg["model"],
            messages=messages,
            max_tokens=1500,
            temperature=0.2,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        raise ProviderUnavailableError(provider, str(e))