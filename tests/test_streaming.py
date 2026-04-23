"""Tests for streaming handlers and StreamingConfig."""

from __future__ import annotations

from agent_loop.streaming.streamer import (
    BufferedStreamHandler,
    NullStreamHandler,
    StreamingConfig,
)


class TestBufferedStreamHandler:
    def test_tokens_accumulate(self):
        h = BufferedStreamHandler()
        h.on_token("hello ")
        h.on_token("world")
        assert h.text == "hello world"

    def test_on_complete_replaces_with_full_text(self):
        h = BufferedStreamHandler()
        h.on_token("partial")
        h.on_complete("full text")
        assert h.text == "full text"

    def test_reset_clears_buffer(self):
        h = BufferedStreamHandler()
        h.on_token("abc")
        h.reset()
        assert h.text == ""

    def test_token_callback_fires(self):
        seen: list[str] = []
        h = BufferedStreamHandler(token_callback=seen.append)
        h.on_token("a")
        h.on_token("b")
        assert seen == ["a", "b"]


class TestNullStreamHandler:
    def test_no_ops(self):
        h = NullStreamHandler()
        h.on_token("x")
        h.on_complete("y")


class TestStreamingConfig:
    def test_defaults(self):
        cfg = StreamingConfig()
        assert cfg.enabled is True
        assert cfg.stream_rationale is False
        assert cfg.stream_hitl_request is True
        assert cfg.stream_final_response is True

    def test_overrides(self):
        cfg = StreamingConfig(
            enabled=False,
            stream_rationale=True,
            stream_hitl_request=False,
            stream_final_response=False,
        )
        assert cfg.enabled is False
        assert cfg.stream_rationale is True
        assert cfg.stream_hitl_request is False
        assert cfg.stream_final_response is False
