"""Sarvam AI SDK wrapper for chat completion API calls."""

import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from backend.config import settings

# Pattern to strip <think>...</think> tags from model output
# Also handles malformed tags: </think without >, <think> without closing, etc.
_THINK_TAG_RE = re.compile(r'<think>.*?</think\s*>?\s*', flags=re.DOTALL)
_THINK_OPEN_RE = re.compile(r'^<think>\s*\n?', flags=re.DOTALL)
_THINK_MALFORMED_RE = re.compile(r'</think\s*>?\s*$', flags=re.DOTALL)


class APIUnavailableError(Exception):
    """Raised when the API is temporarily unavailable (billing, rate limit, etc.)."""
    pass


_client = None
_timeout_pool = ThreadPoolExecutor(max_workers=4)

# Default timeouts (seconds)
_DEFAULT_TIMEOUT = 15   # main answer generation
_SHORT_TIMEOUT = 8      # decision / rewrite / grounding calls

# Sarvam-m context window. Real API limit is 7192 tokens — we keep a safety
# margin below it because the API counts special tokens + message formatting
# overhead that our char-based estimator doesn't.
_MODEL_CONTEXT_WINDOW = 7192
# Larger margin because Sarvam's actual tokenizer counts special tokens and
# occasionally disagrees with our char-based estimate by 300+ tokens on
# system-prompt-heavy calls.
_CONTEXT_SAFETY_MARGIN = 700
# Aggressive char→token ratio. Sarvam-m's tokenizer varies 2.8-3.1 chars/token
# across our prompt shapes — use 2.2 so we always OVER-estimate tokens and
# trim before Sarvam rejects the request.
_CHARS_PER_TOKEN = 2.2
# Per-message overhead Sarvam adds for role/content framing (~4 tokens each).
_PER_MESSAGE_OVERHEAD_TOKENS = 4

# Retry policy: progressive trimming on context overflow, single retry on
# transient network/timeout errors.
_CONTEXT_OVERFLOW_MAX_RETRIES = 3
_CONTEXT_OVERFLOW_SHRINK_RATIO = 0.60  # each retry keeps 60% of previous size
_TRANSIENT_MAX_RETRIES = 1
_TRANSIENT_BACKOFF_SECONDS = 1.5


def _estimate_tokens(messages: list[dict]) -> int:
    """Conservative token count for a messages list."""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return int(total_chars / _CHARS_PER_TOKEN) + len(messages) * _PER_MESSAGE_OVERHEAD_TOKENS


def _trim_middle(text: str, max_chars: int) -> str:
    """Trim the middle of a string, keeping the head and tail intact.

    Used for the user message which has the question at the top and critical
    mandatory-action rules at the bottom — the retrieved context in the middle
    is what we can safely drop.
    """
    if len(text) <= max_chars:
        return text
    # Keep 40% from the start (question + rules header) and 60% at the end
    # (mandatory-action blocks live at the end of the user_message)
    marker = "\n\n...[context truncated to fit model window]...\n\n"
    available = max_chars - len(marker)
    head = max(200, int(available * 0.4))
    tail = max(200, available - head)
    return text[:head] + marker + text[-tail:]


def _fit_to_context_window(messages: list[dict], max_tokens: int) -> list[dict]:
    """Trim messages so estimated prompt + max_tokens stays within model window.

    Strategy:
      1. Drop history messages from the oldest first (index 1 onwards, keeping
         system at 0 and the latest user message at -1).
      2. If still over budget, trim the middle of the latest user message.
    The returned list is safe to send to Sarvam without a 422 context overflow.
    """
    budget = _MODEL_CONTEXT_WINDOW - max_tokens - _CONTEXT_SAFETY_MARGIN
    if budget <= 0:
        return messages  # caller asked for more output than the window allows

    est = _estimate_tokens(messages)
    if est <= budget:
        return messages

    trimmed = list(messages)
    # Drop oldest history first (leave system=0 and latest user=-1 intact)
    while len(trimmed) > 2 and _estimate_tokens(trimmed) > budget:
        dropped = trimmed.pop(1)
        print(f"[SarvamAI] Dropped {dropped.get('role')} history message ({len(dropped.get('content', ''))} chars) to fit context")

    # Still over — shrink the latest user message from the middle
    est = _estimate_tokens(trimmed)
    if est > budget and trimmed:
        last = trimmed[-1]
        other_tokens = est - int(len(last["content"]) / _CHARS_PER_TOKEN) - _PER_MESSAGE_OVERHEAD_TOKENS
        allowed_tokens = budget - other_tokens
        if allowed_tokens > 100:
            allowed_chars = int(allowed_tokens * _CHARS_PER_TOKEN)
            original_len = len(last["content"])
            last["content"] = _trim_middle(last["content"], allowed_chars)
            print(f"[SarvamAI] Trimmed user message {original_len} -> {len(last['content'])} chars to fit context")
    return trimmed


def _get_client():
    """Get cached Sarvam AI client (created once, reused for all calls)."""
    global _client
    if _client is None:
        from sarvamai import SarvamAI
        api_key = settings.sarvam_api_key
        if not api_key:
            raise ValueError(
                "SARVAM_API_KEY is not set. "
                "Add it to .env file in the project root."
            )
        _client = SarvamAI(api_subscription_key=api_key)
    return _client


def ask_with_history(
    system_prompt: str,
    history: list[dict],
    user_message: str,
    max_tokens: int = 1024,
    temperature: float | None = None,
    timeout: float | None = None,
) -> tuple[str, str]:
    """Send a message to Sarvam AI with conversation history and return (text, finish_reason).

    Args:
        system_prompt: System-level instructions.
        history: List of {"role": "user"|"assistant", "content": str} dicts.
        user_message: The current user message to append.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (None = API default).
        timeout: Max seconds to wait for the API response. None = auto-detect
                 (15s for main answers, 8s for short calls).

    Returns:
        Tuple of (content, finish_reason). finish_reason is 'stop', 'length',
        'tool_calls', 'content_filter', or 'function_call'.
        'length' means the response was truncated due to max_tokens.
    """
    client = _get_client()

    # Build messages list: system + last 4 history messages + current message
    # Keep the most recent assistant response in full (users often reference it
    # with "tell me more", "complete the sentence", etc.). Truncate older ones
    # to reduce token count.
    messages = [{"role": "system", "content": system_prompt}]
    recent = history[-4:]
    # Find the index of the last assistant message
    _last_asst_idx = None
    for _i in range(len(recent) - 1, -1, -1):
        if recent[_i]["role"] == "assistant":
            _last_asst_idx = _i
            break
    for _i, msg in enumerate(recent):
        content = msg["content"]
        if msg["role"] == "assistant" and len(content) > 250 and _i != _last_asst_idx:
            # Truncate at last sentence boundary within 300 chars to avoid mid-sentence cuts
            truncated = content[:300]
            # Find the last sentence-ending punctuation
            last_period = max(truncated.rfind('. '), truncated.rfind('.\n'),
                              truncated.rfind('! '), truncated.rfind('!\n'),
                              truncated.rfind('? '), truncated.rfind('?\n'))
            if last_period > 100:  # found a reasonable sentence break
                content = truncated[:last_period + 1]
            else:
                content = content[:250]  # fallback: hard cut
        messages.append({"role": msg["role"], "content": content})
    messages.append({"role": "user", "content": user_message})

    # Safety: trim to fit sarvam-m's 7192-token context window so we never
    # return the "service disruption" fallback due to an HTTP 422 overflow.
    messages = _fit_to_context_window(messages, max_tokens)

    kwargs = {"model": settings.sarvam_model, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature

    # Auto-detect timeout: short calls (decision/grounding) use max_tokens <= 200
    if timeout is None:
        timeout = _SHORT_TIMEOUT if max_tokens <= 200 else _DEFAULT_TIMEOUT

    def _call():
        return client.chat.completions(**kwargs)

    def _is_context_window_error(exc: Exception) -> bool:
        s = str(exc).lower()
        return "context window" in s or "exceeds the model context" in s

    def _is_transient_error(exc: Exception) -> bool:
        """Timeouts, connection drops, and 5xx gateway errors — safe to retry once."""
        s = str(exc).lower()
        if isinstance(exc, FuturesTimeoutError):
            return True
        return any(token in s for token in (
            "timeout", "timed out", "connection", "connection reset",
            "status_code: 5", "502", "503", "504",
            "gateway", "temporarily unavailable", "service unavailable",
        ))

    def _submit_with_timeout():
        return _timeout_pool.submit(_call).result(timeout=timeout)

    try:
        response = None
        overflow_retries = 0
        transient_retries = 0
        while response is None:
            try:
                response = _submit_with_timeout()
            except Exception as exc:
                # Progressive trim on context overflow: each attempt shrinks the
                # user message further until Sarvam accepts it or we exhaust retries.
                if _is_context_window_error(exc) and messages and overflow_retries < _CONTEXT_OVERFLOW_MAX_RETRIES:
                    overflow_retries += 1
                    last = messages[-1]
                    target_chars = max(400, int(len(last["content"]) * _CONTEXT_OVERFLOW_SHRINK_RATIO))
                    shrunk = _trim_middle(last["content"], target_chars)
                    if shrunk == last["content"]:
                        # Can't shrink further — give up
                        raise
                    last["content"] = shrunk
                    kwargs["messages"] = messages
                    print(f"[SarvamAI] context overflow retry {overflow_retries}/{_CONTEXT_OVERFLOW_MAX_RETRIES}: user message trimmed to {len(shrunk)} chars")
                    continue
                # Transient error (timeout / 5xx / connection): brief backoff then retry.
                if _is_transient_error(exc) and transient_retries < _TRANSIENT_MAX_RETRIES:
                    transient_retries += 1
                    print(f"[SarvamAI] transient error ({type(exc).__name__}), retry {transient_retries}/{_TRANSIENT_MAX_RETRIES} after {_TRANSIENT_BACKOFF_SECONDS}s")
                    time.sleep(_TRANSIENT_BACKOFF_SECONDS)
                    continue
                raise
        choice = response.choices[0]
        content = choice.message.content or ""
        finish_reason = getattr(choice, 'finish_reason', 'stop') or 'stop'
        # Normalize: API may return 'length' when max_tokens was hit
        if isinstance(finish_reason, str):
            finish_reason = finish_reason.lower()
        else:
            finish_reason = str(finish_reason).lower()
        # Strip <think>...</think> tags that some models emit
        # Handles malformed variants: </think (no >), unclosed <think>, etc.
        if content:
            content = _THINK_TAG_RE.sub('', content)
            content = _THINK_OPEN_RE.sub('', content)
            content = _THINK_MALFORMED_RE.sub('', content)
        return content.strip(), finish_reason
    except FuturesTimeoutError:
        print(f"[SarvamAI] API call timed out after {timeout}s (max_tokens={max_tokens})")
        raise APIUnavailableError("timeout") from None
    except APIUnavailableError:
        raise
    except Exception as e:
        print(f"[SarvamAI] API error: {e}")
        raise APIUnavailableError("api_error") from e


def ask(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    temperature: float | None = None,
    timeout: float | None = None,
) -> str:
    """Send a single message to Sarvam AI and return the text response (discards finish_reason)."""
    content, _finish_reason = ask_with_history(system_prompt, [], user_message, max_tokens, temperature, timeout=timeout)
    return content
