"""Shared LLM client for cvBuilder scripts."""

from __future__ import annotations

import json
import os
import re
import sys


def parse_llm_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text).strip()

    decoder = json.JSONDecoder()

    def try_decode(s: str) -> dict | None:
        s = s.strip()
        if not s:
            return None
        try:
            obj, _end = decoder.raw_decode(s)
        except json.JSONDecodeError:
            return None
        return obj if isinstance(obj, dict) else None

    obj = try_decode(text)
    if obj is not None:
        return obj

    start = text.find("{")
    if start != -1:
        obj = try_decode(text[start:])
        if obj is not None:
            return obj

    raise SystemExit(
        "LLM returned invalid JSON.\n\n"
        f"First 800 chars:\n{text[:800]}"
    )


def get_provider(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    return os.environ.get("LLM_PROVIDER", "gemini").strip().lower()


def call_openai(system_prompt: str, user_message: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is not set.\n"
            "Edit .env or switch provider: LLM_PROVIDER=gemini"
        )
    if "your-key" in api_key.lower() or api_key == "sk-your-key-here":
        raise SystemExit("OPENAI_API_KEY is still the placeholder. Edit .env")

    from openai import AuthenticationError, OpenAI, RateLimitError

    client = OpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
    except AuthenticationError:
        raise SystemExit("OpenAI rejected your API key (401). Check OPENAI_API_KEY in .env") from None
    except RateLimitError as exc:
        if "insufficient_quota" in str(exc).lower():
            raise SystemExit(
                "OpenAI quota exhausted (429). ChatGPT Plus does NOT include API credits.\n"
                "Use free Gemini instead: set LLM_PROVIDER=gemini and GEMINI_API_KEY in .env\n"
                "  https://aistudio.google.com/apikey"
            ) from None
        raise SystemExit(f"OpenAI rate limit: {exc}") from None

    content = response.choices[0].message.content
    if not content:
        raise SystemExit("OpenAI returned empty response.")
    return parse_llm_json(content)


def call_gemini(system_prompt: str, user_message: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or "your-gemini-key" in api_key.lower():
        raise SystemExit(
            "GEMINI_API_KEY is not set.\n"
            "Free key: https://aistudio.google.com/apikey\n"
            "Add to .env:  GEMINI_API_KEY=...  and  LLM_PROVIDER=gemini"
        )

    import httpx

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={api_key}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
        },
    }

    try:
        response = httpx.post(url, json=payload, timeout=120.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:400]
        if exc.response.status_code == 429:
            raise SystemExit(
                f"Gemini rate limit (429). Wait a minute or try Ollama (local free).\n{body}"
            ) from None
        if exc.response.status_code in (401, 403):
            raise SystemExit(
                f"Gemini rejected API key ({exc.response.status_code}).\n"
                "Get a free key: https://aistudio.google.com/apikey\n"
                f"{body}"
            ) from None
        raise SystemExit(f"Gemini API error ({exc.response.status_code}): {body}") from None
    except httpx.RequestError as exc:
        raise SystemExit(f"Could not reach Gemini API: {exc}") from None

    data = response.json()
    try:
        content = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise SystemExit(f"Unexpected Gemini response: {json.dumps(data)[:500]}") from exc

    if not content:
        raise SystemExit("Gemini returned empty response.")
    return parse_llm_json(content)


def call_ollama(system_prompt: str, user_message: str) -> dict:
    import httpx

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    url = f"{host}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3},
    }

    try:
        response = httpx.post(url, json=payload, timeout=300.0)
        response.raise_for_status()
    except httpx.ConnectError:
        raise SystemExit(
            "Ollama is not running.\n"
            "Install from https://ollama.com\n"
            "Then run:  ollama pull llama3.2  &&  ollama serve\n"
            "Set in .env:  LLM_PROVIDER=ollama"
        ) from None
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:400]
        if "not found" in body.lower():
            raise SystemExit(
                f"Ollama model '{model}' not found.\n"
                f"Run:  ollama pull {model}"
            ) from None
        raise SystemExit(f"Ollama error ({exc.response.status_code}): {body}") from None

    data = response.json()
    content = data.get("message", {}).get("content", "")
    if not content:
        raise SystemExit(f"Ollama returned empty response: {data}")
    return parse_llm_json(content)


def call_llm(system_prompt: str, user_message: str, provider: str) -> dict:
    if provider == "openai":
        return call_openai(system_prompt, user_message)
    if provider == "gemini":
        return call_gemini(system_prompt, user_message)
    if provider == "ollama":
        return call_ollama(system_prompt, user_message)
    raise SystemExit(
        f"Unknown LLM_PROVIDER: {provider!r}\n"
        "Use one of: gemini, ollama, openai"
    )
