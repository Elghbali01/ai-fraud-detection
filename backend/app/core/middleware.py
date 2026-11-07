"""Request identifiers and streaming ASGI byte limits."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4


class RequestIdMiddleware:
    """Attach a non-secret request identifier to state and every response."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_id)


class BodySizeLimitMiddleware:
    """Count incoming ASGI chunks without buffering uploads into application memory."""

    def __init__(self, app, *, json_limit: int, upload_limit: int) -> None:
        self.app = app
        self.json_limit = json_limit
        self.upload_limit = upload_limit

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        is_upload = path == "/api/v1/uploads/csv"
        maximum = self.upload_limit + 256 * 1024 if is_upload else self.json_limit
        total = 0
        exceeded = False
        request_complete = False
        response_messages = []

        async def receive_counted():
            nonlocal total, exceeded, request_complete
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                request_complete = not message.get("more_body", False)
                exceeded = exceeded or total > maximum
                if exceeded:
                    return {"type": "http.disconnect"}
            return message

        async def capture_response(message) -> None:
            response_messages.append(message)

        try:
            await self.app(scope, receive_counted, capture_response)
        except Exception:
            if not exceeded:
                raise
        while not request_complete and not exceeded:
            message = await receive_counted()
            if message["type"] == "http.disconnect":
                break
        if exceeded:
            request_id = scope.get("state", {}).get("request_id", "unknown")
            body = json.dumps(
                {
                    "error": "request_too_large",
                    "message": "Request body exceeds the configured byte limit.",
                    "request_id": request_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            ).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        for message in response_messages:
            await send(message)


class ApiError(Exception):
    """Expected public API error with a safe code and status."""

    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
