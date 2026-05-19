import pytest
from meditatio.services.knowledge_base_service import SearchResult


def test_search_result_structure():
    result = SearchResult(
        kb_id=1,
        kb_name="test",
        document_id=1,
        chunk_id="abc",
        content="test content",
        score=0.9
    )
    assert result.kb_id == 1
    assert result.kb_name == "test"
    assert result.score == 0.9


def test_search_result_to_dict():
    result = SearchResult(
        kb_id=1,
        kb_name="test",
        document_id=1,
        chunk_id="abc",
        content="test content",
        score=0.9
    )
    d = result.to_dict()
    assert d["kb_id"] == 1
    assert d["content"] == "test content"
    assert d["score"] == 0.9