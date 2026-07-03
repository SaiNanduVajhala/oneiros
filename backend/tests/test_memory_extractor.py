import pytest
from unittest.mock import AsyncMock, MagicMock
from domain.memory import MemoryCandidate
from kernel.reasoning.memory_extractor import MemoryExtractor
from kernel.reasoning.llm import ReasoningEngine


@pytest.mark.asyncio
async def test_memory_extractor_chat():
    """Verify that general chat utterances are classified as CHAT and do not extract structured properties."""
    mock_llm = MagicMock(spec=ReasoningEngine)
    mock_llm.generate_structured_response = AsyncMock(return_value={
        "category": "CHAT",
        "subject": None,
        "predicate": None,
        "object": None,
        "confidence": 0.99,
        "reason": "greeting or general informational query"
    })
    
    extractor = MemoryExtractor(mock_llm)
    candidate = await extractor.extract_candidate("Hello, how are you?")
    
    assert candidate.category == "CHAT"
    assert candidate.confidence == 0.99
    assert candidate.subject is None


@pytest.mark.asyncio
async def test_memory_extractor_fact():
    """Verify that durable personal statements are classified as FACT and extract subject/predicate/object."""
    mock_llm = MagicMock(spec=ReasoningEngine)
    mock_llm.generate_structured_response = AsyncMock(return_value={
        "category": "FACT",
        "subject": "user",
        "predicate": "name",
        "object": "Nandu",
        "confidence": 0.95,
        "reason": "statement about the user's name identity"
    })
    
    extractor = MemoryExtractor(mock_llm)
    candidate = await extractor.extract_candidate("My name is Nandu.")
    
    assert candidate.category == "FACT"
    assert candidate.subject == "USER"
    assert candidate.predicate == "identity.name"
    assert candidate.object == "Nandu"
    assert candidate.confidence == 0.95


@pytest.mark.asyncio
async def test_memory_extractor_preference():
    """Verify that likes/dislikes statements are classified as PREFERENCE."""
    mock_llm = MagicMock(spec=ReasoningEngine)
    mock_llm.generate_structured_response = AsyncMock(return_value={
        "category": "PREFERENCE",
        "subject": "user",
        "predicate": "likes",
        "object": "Chemex coffee",
        "confidence": 0.98,
        "reason": "statement about user's coffee preference"
    })
    
    extractor = MemoryExtractor(mock_llm)
    candidate = await extractor.extract_candidate("I like Chemex coffee.")
    
    assert candidate.category == "PREFERENCE"
    assert candidate.subject == "USER"
    assert candidate.predicate == "likes"
    assert candidate.object == "Chemex coffee"
    assert candidate.confidence == 0.98


@pytest.mark.asyncio
async def test_memory_extractor_delete_request():
    """Verify that requests to delete/forget are classified as DELETE_REQUEST."""
    mock_llm = MagicMock(spec=ReasoningEngine)
    mock_llm.generate_structured_response = AsyncMock(return_value={
        "category": "DELETE_REQUEST",
        "subject": "user",
        "predicate": "coffee preference",
        "object": "coffee",
        "confidence": 0.97,
        "reason": "user requested to forget coffee preferences"
    })
    
    extractor = MemoryExtractor(mock_llm)
    candidate = await extractor.extract_candidate("Forget my coffee preference.")
    
    assert candidate.category == "DELETE_REQUEST"
    assert candidate.predicate == "coffee preference"
    assert candidate.object == "coffee"
    assert candidate.confidence == 0.97
