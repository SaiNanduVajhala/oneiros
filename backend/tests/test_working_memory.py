import pytest
from unittest.mock import AsyncMock, MagicMock
from kernel.wake.working_memory import WorkingMemory
from kernel.wake.agent import WakeAgent
from memory.provider import MemoryProvider
from kernel.reasoning.llm import ReasoningEngine

def test_working_memory_limit_and_formatting():
    # Test that WorkingMemory keeps only the last N turns and formats them correctly
    wm = WorkingMemory(max_turns=3)
    
    wm.add_message("user", "Hello 1")
    wm.add_message("assistant", "Hi 1")
    wm.add_message("user", "Hello 2")
    
    # Getting history should contain all 3 messages
    history = wm.get_history()
    assert len(history) == 3
    assert history[0]["content"] == "Hello 1"
    
    # Adding one more message should evict the oldest
    wm.add_message("assistant", "Hi 2")
    history = wm.get_history()
    assert len(history) == 3
    assert history[0]["content"] == "Hi 1"
    assert history[2]["content"] == "Hi 2"
    
    # Check context string formatting
    ctx = wm.get_context_string()
    assert "- Assistant: Hi 1" in ctx
    assert "- User: Hello 2" in ctx
    assert "- Assistant: Hi 2" in ctx
    
    # Clear working memory
    wm.clear()
    assert len(wm.get_history()) == 0
    assert wm.get_context_string() == "- (No recent conversation history)"

@pytest.mark.asyncio
async def test_wake_agent_working_memory_integration():
    # Setup mocks
    mock_provider = MagicMock(spec=MemoryProvider)
    mock_provider.get_graph_data = AsyncMock(return_value=([], []))
    mock_provider.recall = AsyncMock(return_value=[])
    mock_provider.remember = AsyncMock(return_value="mem-123")
    
    mock_reasoning_engine = MagicMock(spec=ReasoningEngine)
    mock_reasoning_engine.reason_wake = AsyncMock(return_value="Mocked response")
    mock_reasoning_engine.generate_structured_response = AsyncMock(return_value={
        "category": "FACT",
        "subject": "user",
        "predicate": "opinion",
        "object": "Chemex coffee is good",
        "confidence": 0.95
    })
    
    # Set up WakeAgent
    agent = WakeAgent(provider=mock_provider, reasoning_engine=mock_reasoning_engine)
    
    # Mock working_memory singleton import inside agent
    # Since agent.py imports working_memory, let's clear it first
    from kernel.wake.working_memory import working_memory
    working_memory.clear()
    
    # Handle user interaction
    user_msg = "Is Chemex coffee good?"
    response = await agent.handle_interaction(user_msg)
    
    assert response["response"] == "Mocked response"
    assert response["memory_id"] == "mem-123"
    
    # Verify that the turn was added to working memory
    history = working_memory.get_history()
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": user_msg}
    assert history[1] == {"role": "assistant", "content": "Mocked response"}
    
    # Cleanup working memory
    working_memory.clear()
