# ADR-0003: Use structlog with JSON output for observability

## Status

Accepted

## Context

The server runs in Azure Container Apps. ACA captures stdout/stderr and
ships it to Log Analytics, where queries are written against structured
fields. Plain-text log messages force log-aggregation-time regex parsing,
which is fragile and expensive.

Alternatives considered:

- **stdlib `logging` + `python-json-logger`**: no extra deps beyond the
  formatter, but no first-class context binding and verbose configuration.
- **loguru**: ergonomic API, but less common in corporate Python and weak
  integration with stdlib loggers used by upstream libraries (uvicorn,
  fastmcp).
- **structlog**: mature, pure-Python, processor pipeline, native context
  binding via `contextvars`, and a stdlib bridge for upstream loggers.

OpenTelemetry was considered for traces/metrics but deferred. The
immediate need is auditable JSON logs; tracing is an orthogonal decision
that can layer on top later without re-architecting logging.

## Decision

Adopt **structlog** as the logging library. `app.logging_config.configure_logging()`
sets up:

- JSON output to stderr (`structlog.processors.JSONRenderer`)
- ISO UTC timestamps (`TimeStamper(fmt="iso", utc=True)`)
- Context binding via `structlog.contextvars.merge_contextvars`
- Stdlib bridge (`structlog.stdlib.ProcessorFormatter`) so upstream
  libraries' loggers also emit JSON
- `LOG_LEVEL` env var (default `INFO`, falls back to `INFO` on invalid
  values)
- Idempotency guard (`_configured` module flag), with `force=True` for
  tests

Audit events use a flat namespace:

- `auth.token.invalid`, `auth.token.rejected`, `auth.token.accepted`
- `mcp.client.connected`
- `mcp.tool.call.start`, `mcp.tool.call.success`, `mcp.tool.call.error`

Token strings, tool arguments, and return values are **never** logged.

## Consequences

Positive:

- Log Analytics queries can filter on structured fields
  (`event="auth.token.rejected" | subject="..."`).
- Context binding carries request-scoped data (`request_id`, `client_ip`) and
  `client_session` is attached from the MCP session context on each request
  without thread-local boilerplate.
- Stdlib bridge means uvicorn and fastmcp logs are JSON too.
- Sensitive payloads (token, args, return) are excluded by design; the
  test suite enforces this with explicit secret-leak guards.

Negative:

- New runtime dependency (`structlog`).
- Developers must remember to use `structlog.get_logger()` and not
  `logging.getLogger()` to get the configured pipeline (though the stdlib
  bridge mitigates this for accidental usage).
- JSON is harder to read in a terminal during local development; no
  dev-friendly renderer is currently configured.
