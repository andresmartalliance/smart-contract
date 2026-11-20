"""Local, evidence-only PDF preview remains safe during Gemini outages."""
import io

from fastapi import HTTPException
from app.main import app
from app.routers import maira


def test_numbered_pdf_layout_groups_source_roles_without_generating_arrows(monkeypatch):
    class FakePage:
        class Box:
            width = 768
            height = 576
        mediabox = Box()
        def extract_text(self, visitor_text=None):
            fragments = [
                ("1", 110, 450, 16),
                ("REGISTRO DE", 96, 414, 15),
                ("PERSONAL", 98, 399, 15),
                ("ASPIRANTE", 99, 369, 15),
                ("2", 320, 450, 16),
                ("VERIFICACIÓN DE", 300, 414, 15),
                ("DOCUMENTOS", 305, 399, 15),
                ("JURIDICO", 310, 369, 15),
            ]
            for text, x, y, size in fragments:
                visitor_text(text, [1, 0, 0, 1, x, y], [1, 0, 0, 1, 0, 0], None, size)
    class FakeReader:
        pages = [FakePage()]
    import pypdf
    monkeypatch.setattr(pypdf, "PdfReader", lambda *args, **kwargs: FakeReader())
    steps = maira._numbered_pdf_steps(b"%PDF-1.4 synthetic")
    assert [step["source_step"] for step in steps] == ["1", "2"]
    assert [step["role"] for step in steps] == ["ASPIRANTE", "JURIDICO"]
    assert all(step["depends_on"] is None for step in steps)
    proposal = maira._compile_source_extraction({"steps": steps})
    assert len(proposal.source_map) == 2
    assert proposal.workflow.metadata["requires_review"] is True
    assert proposal.workflow.metadata["inferred_dependency_count"] == 1


def test_source_only_route_auth_no_gemini_calls(testing, monkeypatch):
    client, _ = testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY", "fake")
    app.dependency_overrides[maira._verify_identity] = lambda: "authorized@example.com"
    async def forbidden(*args, **kwargs):
        raise AssertionError("Must not call Gemini")
    monkeypatch.setattr(maira, "_call_gemini", forbidden)
    monkeypatch.setattr(maira, "_numbered_pdf_steps", lambda data: [
        {"source_step": "1", "label": "Registro de personal", "source_excerpt": "REGISTRO DE PERSONAL",
         "role": "ASPIRANTE", "kind": "FORM", "page": 1, "confidence": "baja", "depends_on": None},
        {"source_step": "2", "label": "Verificación de documentos", "source_excerpt": "VERIFICACIÓN DE DOCUMENTOS",
         "role": "JURIDICO", "kind": "VALIDATION", "page": 1, "confidence": "baja", "depends_on": None},
    ])
    try:
        response = client.post("/api/v1/maira/workflow-import/source-preview",
                               files={"file": ("flow.pdf", b"%PDF-1.4 synthetic", "application/pdf")},
                               data={"party_kind": "JURIDICA"})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["analysis_method"] == "PDF_TEXT_ONLY"
        assert payload["mapped_steps"] == 2
        assert payload["status"] == "DRAFT_FOR_HUMAN_REVIEW"
        assert payload["workflow"]["metadata"]["source_method"] == "PDF_TEXT_ONLY"
        assert payload["workflow"]["metadata"]["roles_verified"] is False
        assert payload["workflow"]["metadata"]["dependencies_verified"] is False
        assert payload["workflow"]["metadata"]["draft"] is True
        assert payload["workflow"]["metadata"]["inferred_dependency_count"] == 1
        assert any("sin Gemini" in note for note in payload["observations"])
        assert any("flechas" in q.lower() for q in payload["questions"])
    finally:
        app.dependency_overrides.pop(maira._verify_identity, None)


def test_source_only_rejects_non_pdf(testing, monkeypatch):
    client, _ = testing
    app.dependency_overrides[maira._verify_identity] = lambda: "authorized@example.com"
    try:
        response = client.post("/api/v1/maira/workflow-import/source-preview",
                               files={"file": ("notes.txt", b"Document text", "text/plain")})
        assert response.status_code == 415
    finally:
        app.dependency_overrides.pop(maira._verify_identity, None)


def test_source_only_requires_google_auth(testing, monkeypatch):
    client, _ = testing
    monkeypatch.delenv("SMART_GOOGLE_CLIENT_ID", raising=False)
    response = client.post("/api/v1/maira/workflow-import/source-preview",
                           files={"file": ("flow.pdf", b"%PDF-1.4 sample", "application/pdf")})
    assert response.status_code == 503

def test_document_sources_cannot_publish_without_review():
    from app.routers.portals import _requires_source_review
    from app.workflow.schema import WorkflowDefinition
    from tests.test_maira_import import valid_proposal
    raw = valid_proposal()["workflow"]
    raw["nodes"][1].setdefault("config", {})["source_step"] = "2.1"
    workflow = WorkflowDefinition.model_validate(raw)
    assert _requires_source_review(workflow)
    workflow.metadata["review_confirmed"] = True
    assert not _requires_source_review(workflow)

def test_maira_questions_are_required_before_publication():
    from app.routers.portals import _missing_maira_dialogue
    from app.workflow.schema import WorkflowDefinition
    from tests.test_maira_import import valid_proposal
    raw = valid_proposal()["workflow"]
    raw["metadata"] = {"source":"maira-document-import","review_confirmed":True}
    workflow = WorkflowDefinition.model_validate(raw)
    assert _missing_maira_dialogue(workflow)
    workflow.metadata["maira_dialogue"] = {
       "scope_decision":"ADAPT_TO_ENTITY", "completed":True,
       "questions_total":2,
       "answers":[{"question":"¿Cómo se adapta el proceso?", "answer":"Revisar requisitos y responsables institucionales"}]
    }
    assert not _missing_maira_dialogue(workflow)
    workflow.metadata["maira_dialogue"]["answers"][0]["answer"]=""
    assert _missing_maira_dialogue(workflow)


def test_ordinary_workflow_not_blocked_by_maira_questions():
    from app.routers.portals import _missing_maira_dialogue
    from app.workflow.schema import WorkflowDefinition
    from tests.test_maira_import import valid_proposal
    raw = valid_proposal()["workflow"]
    raw["metadata"] = {"source":"smart-contract-workflow-studio"}
    for node in raw["nodes"]:
        node.get("config", {}).pop("source_step", None)
    wf = WorkflowDefinition.model_validate(raw)
    assert not _missing_maira_dialogue(wf)
