"""No-network safety checks for the Gemini PDF text recovery path."""
import asyncio
from unittest.mock import AsyncMock

import httpx
from fastapi import HTTPException
import pytest

from app.routers import maira


class SequenceClient:
    def __init__(self, items):
        self.items = list(items)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *unused):
        return False

    async def post(self, url, headers, json):
        self.calls.append(json)
        return self.items.pop(0)


def stub(monkeypatch, statuses):
    fake = SequenceClient([
        httpx.Response(s, json={"error": {"status": "UNAVAILABLE"}} if s != 200 else
                       {"candidates": [{"finishReason": "STOP", "content": {"parts": [
                           {"text": '{"steps":[{"source_step":"1","label":"Registro","source_excerpt":"REGISTRO","role":"ASPIRANTE","kind":"FORM","page":1,"confidence":"alta","depends_on":[]},{"source_step":"2","label":"Verificación","source_excerpt":"VERIFICACION","role":"JURIDICO","kind":"VALIDATION","page":1,"confidence":"alta","depends_on":["1"]}],"observations":[],"questions":[]}'}]}}]})
        for s in statuses
    ])
    monkeypatch.setattr(maira.httpx, "AsyncClient", lambda timeout: fake)
    monkeypatch.setattr(maira.asyncio, "sleep", AsyncMock())
    return fake


def test_pdf_503_uses_text_fallback_without_repeating_pdf(monkeypatch):
    fake = stub(monkeypatch, [503, 200])
    initial = {"contents":[{"parts":[{"inline_data":{"mime_type":"application/pdf","data":"fake"}}]}]}
    reduced = {"contents":[{"parts":[{"text":"texto del diagrama"}]}]}
    result = asyncio.run(maira._post_gemini(initial,"secret","gemini-3.6-flash",30,
                                         fallback_request=reduced))
    assert len(fake.calls) == 2
    assert fake.calls == [initial, reduced]
    assert result["_maira_fallback_used"] is True


def test_pdf_503_both_modes_fail_closed(monkeypatch):
    fake = stub(monkeypatch,[503,503])
    with pytest.raises(HTTPException) as err:
        asyncio.run(maira._post_gemini({"id":"pdf"},"secret","gemini-3.6-flash",30,
                                       fallback_request={"id":"text"}))
    assert err.value.status_code == 502
    assert "texto extraído" in err.value.detail
    assert len(fake.calls) == 2


def test_pdf_text_recovery_never_publishes_arrows_guessed_by_model(monkeypatch):
    fake = stub(monkeypatch,[503,200])
    monkeypatch.setattr(maira,"_pdf_text_for_fallback",lambda data:"REGISTRO DE PERSONAL. VERIFICACION DE DOCUMENTOS")
    # Deliberately synthetic PDF: bypass source validation only for this unit test.
    proposal = asyncio.run(maira._call_gemini(b"%PDF-1.4 fake",".pdf","diagrama.pdf","secret","JURIDICA"))
    assert len(fake.calls)==2
    assert proposal.workflow.metadata["draft"] is True
    assert proposal.workflow.metadata["requires_review"] is True
    assert proposal.workflow.metadata["inferred_dependency_count"] == 1
    assert len(proposal.source_map) == 2
    assert any("NO se verificaron visualmente" in s for s in proposal.observations)
    assert any("Dependencias provisionales" in s for s in proposal.observations)
    assert proposal.workflow.nodes[1].config["actor_side"]=="CONTRATISTA"


def test_unextractable_pdf_keeps_original_path(monkeypatch):
    monkeypatch.setattr(maira,"_pdf_text_for_fallback",lambda data:None)
    collected = {}
    async def fake_post(request,key,model,timeout):
        collected["parts"]=request["contents"][0]["parts"]
        return {"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":'{"steps":[{"source_step":"1","label":"Registro","source_excerpt":"REGISTRO","role":"ASPIRANTE","kind":"FORM","depends_on":[]}],"questions":[],"observations":[]}'}]}}]}
    monkeypatch.setattr(maira,"_post_gemini",fake_post)
    proposal=asyncio.run(maira._call_gemini(b"%PDF-1.4 fake",".pdf","diagrama.pdf","secret"))
    assert len(collected["parts"])==2
    assert "inline_data" in collected["parts"][1]
    assert proposal.workflow.metadata["inferred_dependency_count"]==0
