import os
import ollama
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROVIDERS = {
    "ollama": {
        "label": "Local (phi3)",
        "model": "phi3",
    },
    "groq": {
        "label": "Groq (Llama 3.3 70B)",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
    },
    "gemini": {
        "label": "Google Gemini Flash",
        "model": "gemini-3.8-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
    },
}


def available_providers():
    """Ollama is always listed. Others appear only if their API key is set in .env."""
    out = []
    for pid, cfg in PROVIDERS.items():
        if pid == "ollama" or os.getenv(cfg.get("key_env", "")):
            out.append({"id": pid, "label": cfg["label"]})
    return out


def _get_cfg(provider):
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        raise ValueError(f"Unknown provider: {provider}")
    return cfg


def _hosted_client(cfg):
    api_key = os.getenv(cfg["key_env"])
    if not api_key:
        raise ValueError(f"{cfg['key_env']} is missing in .env")
    return OpenAI(api_key=api_key, base_url=cfg["base_url"])


def generate(messages, provider="ollama", ollama_model=None):
    """Full answer at once. messages = [{"role": "...", "content": "..."}]"""
    cfg = _get_cfg(provider)

    if provider == "ollama":
        res = ollama.chat(
            model=ollama_model or cfg["model"],
            messages=messages,
            options={"num_predict": 400, "num_ctx": 2048, "temperature": 0.2},
            keep_alive="30m",
        )
        return res["message"]["content"]

    client = _hosted_client(cfg)
    res = client.chat.completions.create(
        model=cfg["model"], messages=messages, max_tokens=800, temperature=0.2
    )
    return res.choices[0].message.content


def generate_stream(messages, provider="ollama", ollama_model=None):
    """Yields the answer piece by piece."""
    cfg = _get_cfg(provider)

    if provider == "ollama":
        stream = ollama.chat(
            model=ollama_model or cfg["model"],
            messages=messages,
            options={"num_predict": 400, "num_ctx": 2048, "temperature": 0.2},
            keep_alive="30m",
            stream=True,
        )
        for part in stream:
            yield part["message"]["content"]
        return

    client = _hosted_client(cfg)
    stream = client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        max_tokens=800,
        temperature=0.2,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content