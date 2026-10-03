"""Thin wrapper over the Anthropic SDK: one structured-output call, with cost
accounting and a hard budget guard so a rerun can never blow the credit."""

import json
import os
import threading

import anthropic
from dotenv import load_dotenv

from .paths import ROOT, WORK

load_dotenv(ROOT / "backend" / ".env")

MODEL = os.getenv("EXTRACT_MODEL", "claude-sonnet-5")
BUDGET_USD = float(os.getenv("LLM_BUDGET_USD", "15"))
# $ per 1M tokens (input, output) - Claude API first-party pricing.
PRICES = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
SPEND_FILE = WORK / "llm_spend.json"
_lock = threading.Lock()


class BudgetExceeded(RuntimeError):
    pass


def _load_spend() -> dict:
    if SPEND_FILE.exists():
        return json.loads(SPEND_FILE.read_text())
    return {"usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0}


def spent_usd() -> float:
    return _load_spend()["usd"]


def _record(model: str, usage) -> float:
    pin, pout = PRICES.get(model, PRICES["claude-opus-5"])
    cache_w = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_r = getattr(usage, "cache_read_input_tokens", 0) or 0
    cost = (usage.input_tokens * pin + cache_w * pin * 1.25 + cache_r * pin * 0.1
            + usage.output_tokens * pout) / 1e6
    with _lock:
        s = _load_spend()
        s["usd"] += cost
        s["calls"] += 1
        s["input_tokens"] += usage.input_tokens + cache_w + cache_r
        s["output_tokens"] += usage.output_tokens
        SPEND_FILE.parent.mkdir(parents=True, exist_ok=True)
        SPEND_FILE.write_text(json.dumps(s, indent=1))
    return cost


_client: anthropic.AsyncAnthropic | None = None


def client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        # Org-level keys (not scoped to a workspace) must name the workspace per request.
        ws = os.getenv("ANTHROPIC_WORKSPACE_ID")
        headers = {"anthropic-workspace-id": ws} if ws else None
        _client = anthropic.AsyncAnthropic(max_retries=4, default_headers=headers)
    return _client


async def structured_call(system: str, user: str, schema: dict, *, effort: str = "medium",
                          max_tokens: int = 32000, model: str = MODEL) -> tuple[dict, dict]:
    """Return (parsed JSON, meta). Raises BudgetExceeded before spending past the cap."""
    if spent_usd() >= BUDGET_USD:
        raise BudgetExceeded(f"LLM budget of ${BUDGET_USD:.2f} reached")
    async with client().messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        thinking={"type": "adaptive"},
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    ) as stream:
        msg = await stream.get_final_message()
    cost = _record(model, msg.usage)
    meta = {"model": model, "request_id": getattr(msg, "_request_id", None) or msg.id, "stop_reason": msg.stop_reason,
            "input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
            "cost_usd": round(cost, 4)}
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {meta}")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError(f"output truncated at max_tokens: {meta}")
    text = next(b.text for b in msg.content if b.type == "text")
    return json.loads(text), meta
