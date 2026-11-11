"""Thin wrapper around the Gemini API: one shared client, rate limiting and automatic retries.

Every script that calls Gemini goes through here, so we never exceed the free-tier
limits and temporary errors (429 / 5xx) are retried with a pause.
"""
import logging
import time

from google import genai
from google.genai import errors, types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

import config

log = logging.getLogger("rag")
_client = None

# The google-genai and httpx libraries log every request at INFO level, which drowns our own
# progress lines. Only show their warnings and errors.
for _noisy_logger in ("httpx", "httpcore", "google_genai", "google.genai"):
    logging.getLogger(_noisy_logger).setLevel(logging.WARNING)


def get_client() -> genai.Client:
    """Create the Gemini client once and reuse it."""
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is empty. Fill in your .env file.")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


class RateLimiter:
    """Spaces calls out so we stay under a limit of `per_minute` units per minute.

    `weight` lets one call count as several units (e.g. a batch of 10 texts = 10 units).
    """

    def __init__(self, per_minute: float):
        self.interval = 60.0 / max(1.0, per_minute)
        self._next_allowed = 0.0

    def wait(self, weight: float = 1.0) -> None:
        now = time.monotonic()
        delay = self._next_allowed - now
        if delay > 0:
            time.sleep(delay)
        self._next_allowed = max(now, self._next_allowed) + self.interval * weight


generation_limiter = RateLimiter(config.REQUESTS_PER_MINUTE)
# Embedding free tier: 100 requests/min and 30K tokens/min. Counting each TEXT as one unit
# (about 250 tokens for a document chunk) keeps us safely inside both limits.
embedding_limiter = RateLimiter(100)


def _is_retryable(error: BaseException) -> bool:
    """Retry only temporary problems: rate limit (429) and server errors (5xx)."""
    return isinstance(error, errors.APIError) and getattr(error, "code", None) in (429, 500, 502, 503, 504)


retry_policy = retry(retry=retry_if_exception(_is_retryable), stop=stop_after_attempt(5),
                     wait=wait_exponential(multiplier=5, min=5, max=60), reraise=True)


@retry_policy
def _call_model(model: str, prompt: str, generation_config: types.GenerateContentConfig):
    generation_limiter.wait()
    return get_client().models.generate_content(model=model, contents=prompt, config=generation_config)


def generate_json(prompt: str, schema, model: str, system: str | None = None, temperature: float = 0.7):
    """Ask Gemini for JSON that matches a pydantic `schema` and return it as a validated object."""
    generation_config = types.GenerateContentConfig(
        system_instruction=system, temperature=temperature,
        response_mime_type="application/json", response_schema=schema)
    response = _call_model(model, prompt, generation_config)
    return schema.model_validate_json(response.text)


def generate_text(prompt: str, model: str, system: str | None = None, temperature: float = 0.7) -> str:
    """Ask Gemini for plain text."""
    generation_config = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
    text = (_call_model(model, prompt, generation_config).text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty answer (it may have been blocked). Try again.")
    return text


@retry_policy
def _call_embed(texts: list, task_type: str):
    embedding_limiter.wait(weight=len(texts))
    return get_client().models.embed_content(
        model=config.EMBED_MODEL, contents=texts,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=config.EMBED_DIM))


def embed_texts(texts: list, task_type: str = "RETRIEVAL_DOCUMENT", batch_size: int = 10) -> list:
    """Turn texts into vectors. Use RETRIEVAL_DOCUMENT for knowledge-base chunks and
    RETRIEVAL_QUERY for the ticket text you search with (Gemini tunes each differently)."""
    vectors = []
    for start in range(0, len(texts), batch_size):
        response = _call_embed(texts[start:start + batch_size], task_type)
        vectors.extend(item.values for item in response.embeddings)
    return vectors
