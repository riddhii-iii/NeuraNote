import os
import openai


def _set_api_key():
    openai.api_key = os.getenv("OPENAI_API_KEY")


def get_embedding(text: str) -> list[float]:
    _set_api_key()
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    response = openai.Embedding.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response["data"][0]["embedding"]


def completion(prompt: str, system_prompt: str | None = None, max_tokens: int = 400) -> str:
    _set_api_key()
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.2,
        max_tokens=max_tokens,
    )

    return response["choices"][0]["message"]["content"].strip()
