"""
Unit tests for MCPClient.call_tool method.

Covers: normal async call, None/empty arguments, error propagation,
session not initialized, and type validation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Import the class under test
# ---------------------------------------------------------------------------

from mcp_local.client import MCPClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    """Return an AsyncMock simulating a connected ClientSession."""
    session = AsyncMock()
    session.call_tool = AsyncMock(return_value={"content": "result"})
    return session


@pytest.fixture
def connected_client(mock_session):
    """Create an MCPClient with a pre-injected mock session (bypassing connect)."""
    client = MCPClient(command="npx", args=["-y", "@anthropic/mcp-browser"])
    client.session = mock_session
    return client


# ---------------------------------------------------------------------------
# Normal flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_tool_returns_result(connected_client, mock_session):
    """call_tool should delegate to session.call_tool and return its result."""
    mock_session.call_tool.return_value = {"content": "browser opened"}

    result = await connected_client.call_tool("browser_navigate", {"url": "https://example.com"})

    assert result == {"content": "browser opened"}
    mock_session.call_tool.assert_awaited_once_with("browser_navigate", {"url": "https://example.com"})


@pytest.mark.asyncio
async def test_call_tool_passes_arguments_correctly(connected_client, mock_session):
    """Verify name and arguments are forwarded to session.call_tool unchanged."""
    mock_session.call_tool.return_value = "ok"

    await connected_client.call_tool("click", {"selector": "#btn", "x": 100})

    mock_session.call_tool.assert_awaited_once_with("click", {"selector": "#btn", "x": 100})


@pytest.mark.asyncio
async def test_call_tool_with_multiple_calls(connected_client, mock_session):
    """Multiple successive calls should each invoke session.call_tool."""
    mock_session.call_tool.side_effect = ["result1", "result2"]

    r1 = await connected_client.call_tool("navigate", {"url": "/page1"})
    r2 = await connected_client.call_tool("screenshot", {})

    assert r1 == "result1"
    assert r2 == "result2"
    assert mock_session.call_tool.await_count == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_tool_with_empty_arguments(connected_client, mock_session):
    """Empty dict arguments should be forwarded as-is."""
    mock_session.call_tool.return_value = "empty_result"

    result = await connected_client.call_tool("refresh", {})

    assert result == "empty_result"
    mock_session.call_tool.assert_awaited_once_with("refresh", {})


@pytest.mark.asyncio
async def test_call_tool_with_empty_name(connected_client, mock_session):
    """Empty tool name should still be forwarded (validation is server-side)."""
    mock_session.call_tool.return_value = None

    result = await connected_client.call_tool("", {"key": "val"})

    assert result is None
    mock_session.call_tool.assert_awaited_once_with("", {"key": "val"})


@pytest.mark.asyncio
async def test_call_tool_with_none_arguments(connected_client, mock_session):
    """None arguments should be forwarded as-is."""
    mock_session.call_tool.return_value = "ok"

    result = await connected_client.call_tool("status", None)

    assert result == "ok"
    mock_session.call_tool.assert_awaited_once_with("status", None)


@pytest.mark.asyncio
async def test_call_tool_with_large_arguments(connected_client, mock_session):
    """Large argument payloads should be handled correctly."""
    large_args = {"data": "x" * 10000, "nested": {"key": list(range(100))}}
    mock_session.call_tool.return_value = "done"

    result = await connected_client.call_tool("process", large_args)

    assert result == "done"


@pytest.mark.asyncio
async def test_call_tool_returns_none(connected_client, mock_session):
    """When session returns None, call_tool should return None."""
    mock_session.call_tool.return_value = None

    result = await connected_client.call_tool("close", {})

    assert result is None


@pytest.mark.asyncio
async def test_call_tool_with_special_chars_in_name(connected_client, mock_session):
    """Tool names with special characters should be forwarded correctly."""
    mock_session.call_tool.return_value = "ok"

    result = await connected_client.call_tool("mcp__browser_navigate", {"url": "/test"})

    assert result == "ok"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_tool_session_not_initialized():
    """When session is None (not connected), call_tool should raise AttributeError."""
    client = MCPClient(command="npx")
    client.session = None

    with pytest.raises(AttributeError):
        await client.call_tool("any_tool", {})


@pytest.mark.asyncio
async def test_call_tool_session_call_tool_raises(connected_client, mock_session):
    """Exceptions from session.call_tool should propagate to caller."""
    mock_session.call_tool.side_effect = ConnectionError("MCP server unreachable")

    with pytest.raises(ConnectionError, match="MCP server unreachable"):
        await connected_client.call_tool("navigate", {"url": "/"})


@pytest.mark.asyncio
async def test_call_tool_session_call_tool_raises_timeout(connected_client, mock_session):
    """TimeoutError from session should propagate."""
    mock_session.call_tool.side_effect = TimeoutError("call timed out")

    with pytest.raises(TimeoutError, match="call timed out"):
        await connected_client.call_tool("slow_tool", {})


@pytest.mark.asyncio
async def test_call_tool_session_call_tool_raises_value_error(connected_client, mock_session):
    """ValueError (e.g., invalid tool name from server) should propagate."""
    mock_session.call_tool.side_effect = ValueError("Unknown tool: invalid_tool")

    with pytest.raises(ValueError, match="Unknown tool"):
        await connected_client.call_tool("invalid_tool", {})


# ---------------------------------------------------------------------------
# Integration-style (still mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_tool_after_connect_simulation():
    """Simulate a full connect -> call_tool flow with mocked transport."""
    client = MCPClient(command="echo", args=["hello"])

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value="from_server")

    client.session = mock_session

    await client.session.initialize()
    result = await client.call_tool("test_tool", {"arg": 1})

    assert result == "from_server"
    mock_session.initialize.assert_awaited_once()
    mock_session.call_tool.assert_awaited_once_with("test_tool", {"arg": 1})
