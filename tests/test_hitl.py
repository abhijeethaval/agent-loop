"""Tests for HITL handlers."""

from __future__ import annotations

import pytest

from agent_loop.hitl.handler import (
    AsyncHITLHandler,
    CallbackHITLHandler,
    HITLPendingError,
)


class TestCallbackHITLHandler:
    def test_forwards_to_callback(self):
        received: list[str] = []

        def cb(req: str) -> str:
            received.append(req)
            return "the answer"

        handler = CallbackHITLHandler(cb)
        result = handler.request_human_input("what?")
        assert result == "the answer"
        assert received == ["what?"]


class TestAsyncHITLHandler:
    def test_request_raises_and_queues(self):
        handler = AsyncHITLHandler()
        assert not handler.has_pending_request

        with pytest.raises(HITLPendingError) as excinfo:
            handler.request_human_input("need input")

        assert excinfo.value.request == "need input"
        assert handler.has_pending_request
        assert handler.pending_request == "need input"

    def test_provide_and_get_response(self):
        handler = AsyncHITLHandler()
        with pytest.raises(HITLPendingError):
            handler.request_human_input("q")

        handler.provide_response("a")
        assert not handler.has_pending_request
        assert handler.get_response() == "a"

    def test_get_response_without_provide_raises(self):
        handler = AsyncHITLHandler()
        with pytest.raises(ValueError):
            handler.get_response()

    def test_get_response_consumes(self):
        handler = AsyncHITLHandler()
        with pytest.raises(HITLPendingError):
            handler.request_human_input("q")
        handler.provide_response("a")
        assert handler.get_response() == "a"
        with pytest.raises(ValueError):
            handler.get_response()
