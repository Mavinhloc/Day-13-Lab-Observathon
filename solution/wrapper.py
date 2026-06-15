"""YOUR mitigation + observability layer. The simulator calls mitigate() around the
opaque agent (a REAL LLM) for every request. This is the ONLY place observability can
live -- the agent is silent. Legal moves: retry / cache / route / guardrail / sanitize
/ fallback / session-reset / PROMPT ROUTING, plus your own logging/tracing/metrics.
Illegal: hardcoding answers, importing the agent internals, reading instructor files,
network exfiltration.

  call_next(question, config) -> result   # the only way to reach the black box
  context = {"session_id","turn_index","qid","cache": <shared dict>, "cache_lock": <Lock>}
  result  = {"answer","status","steps","trace","meta":{latency_ms,usage,...}}

PROMPT ROUTING: you can override the agent's system prompt PER REQUEST by setting it in
the config you pass to call_next, e.g.:
    conf = dict(config); conf["system_prompt"] = my_better_prompt
    result = call_next(question, conf)
(Or just edit solution/prompt.txt for a single static prompt used on every request.)
"""
from __future__ import annotations

# You may reuse the Day 13 toolkit, e.g.:
# from telemetry.logger import logger
# from telemetry.cost import cost_from_usage
# from telemetry.redact import redact


def mitigate(call_next, question, config, context):
    import time, sys
    qid = context.get("qid", "?")
    turn = context.get("turn_index", "?")
    t0 = time.time()
    try:
        result = call_next(question, config)
        meta = result.get("meta", {}) if result else {}
        wall_ms = int((time.time() - t0) * 1000)
        latency_ms = meta.get("latency_ms", wall_ms)
        usage = meta.get("usage", {})
        tokens = usage.get("total_tokens", "?")
        tools = meta.get("tools_used", [])
        steps = result.get("steps", "?") if result else "?"
        status = result.get("status", "?") if result else "?"
        print(
            f"[obs] qid={qid} turn={turn} status={status} steps={steps} "
            f"latency={latency_ms}ms tokens={tokens} tools={len(tools)}",
            file=sys.stderr, flush=True
        )
        return result
    except Exception as e:
        wall_ms = int((time.time() - t0) * 1000)
        print(f"[obs] qid={qid} turn={turn} ERROR {type(e).__name__} wall={wall_ms}ms: {e}", file=sys.stderr, flush=True)
        raise
