"""Real-document reference for MAIRA's workflow compiler.

Transcribed from the user-supplied two-page diagram
"Process Flowchart clico contract V2.pdf", 19 November 2026.
This is a TEST FIXTURE only. It does not configure an institutional workflow,
prove Gemini's live extraction, or grant execution/publication permission.
"""
from app.routers.maira import _compile_source_extraction


# Source step, verbatim visible activity, verbatim visible responsible party,
# conservative task classification, and source page.
SOURCE = [
    ("1", "CREACIÓN DE USUARIOS Y PROYECTOS", "ADMINISTRADOR", "FORM", 1),
    ("2", "REGISTRO DE PERSONAL A CONTRATAR", "ASPIRANTE", "FORM", 1),
    ("2.1", "CORREO CON DOCUMENTOS DEL ASPIRANTE", "SISTEMA", "NOTIFICATION", 1),
    ("3", "VERIFICACIÓN DE DOCUMENTOS CARGADOS", "JURIDICO", "DOCUMENT_REVIEW", 1),
    ("4", "CORREO APROBACIÓN DOCUMENTOS", "SISTEMA", "NOTIFICATION", 1),
    ("4.1", "CORREO SOLICITUD DE PRESUPUESTAL", "SISTEMA", "NOTIFICATION", 1),
    ("5", "SOLICITUD DE REGISTRO PRESUPUESTAL", "SUPERVISOR", "DOCUMENT_REQUEST", 1),
    ("5.1", "CORREO DE SOLICITUD REG. PRESUPUESTAL", "SISTEMA", "NOTIFICATION", 1),
    ("6", "CARGA Y APROBACIÓN DE REG. P", "FINANCIERO", "APPROVAL", 1),
    ("6.1", "CORREO CARGA R. PRESUPUESTAL", "SISTEMA", "NOTIFICATION", 1),
    ("7", "CREACION DEL CONTRATO", "JURIDICO", "DOCUMENT_GENERATION", 1),
    ("7.1", "CORREO CREACIÓN DE CONTRATO", "SISTEMA", "NOTIFICATION", 2),
    ("8", "FIRMA DE CONTRATO", "ASPIRANTE", "SIGNATURE", 2),
    ("8.1", "CORREO CON CONTRATO DEL ASPIRANTE", "SISTEMA", "NOTIFICATION", 2),
    ("8.2", "CORREO AL SUPERVISOR", "SISTEMA", "NOTIFICATION", 2),
    ("9", "TRÁMITE DE PÓLIZA Y CARGA DOCUMENTO", "SUPERVISOR", "DOCUMENT_REQUEST", 2),
    ("9.1", "CORREO DE CARGA", "SISTEMA", "NOTIFICATION", 2),
    ("10", "APROBACIÓN DE POLIZA", "JURIDICO", "APPROVAL", 2),
    ("10.1", "CORREO APROBACIÓN POLIZA", "SISTEMA", "NOTIFICATION", 2),
    ("11", "INFORMACIÓN AFILIACIÓN ARL", "SUPERVISOR", "FORM", 2),
    ("12", "CARGA CERTIFICACIÓN ARL", "SST", "DOCUMENT_REQUEST", 2),
    ("12.1", "NOTIFICACIÓN DE CERTIFICADO", "SISTEMA", "NOTIFICATION", 2),
    ("13", "ACTA DE INICIO", "SUPERVISOR", "DOCUMENT_GENERATION", 2),
]


def _fixture():
    steps = []
    for index, (number, excerpt, role, kind, page) in enumerate(SOURCE):
        steps.append({
            "source_step": number,
            "label": excerpt.title(),
            "source_excerpt": excerpt,
            "role": role,
            "kind": kind,
            "page": page,
            "confidence": "alta",
            # Diagram arrows are legible, forming one chain across both pages.
            "depends_on": [SOURCE[index - 1][0]] if index else [],
        })
    return {
        "steps": steps,
        "questions": [],
        "observations": [
            "Fuente: contratación de personal/aspirantes. "
            "La pertinencia para una IPS persona jurídica requiere revisión."
        ],
    }


def test_document_reference_has_23_visible_activities_in_two_pages():
    assert len(SOURCE) == 23
    assert [s[0] for s in SOURCE] == [
        "1", "2", "2.1", "3", "4", "4.1", "5", "5.1", "6", "6.1",
        "7", "7.1", "8", "8.1", "8.2", "9", "9.1", "10",
        "10.1", "11", "12", "12.1", "13",
    ]
    assert sum(s[4] == 1 for s in SOURCE) == 11
    assert sum(s[4] == 2 for s in SOURCE) == 12


def test_document_reference_compiles_without_lost_steps_or_invented_edges():
    proposal = _compile_source_extraction(_fixture())
    workflow = proposal.workflow
    assert len(proposal.source_map) == 23
    assert len(workflow.nodes) == 25  # 23 documentary + 2 technical
    assert len(workflow.edges) == 24  # START, 22 transitions, END
    assert workflow.metadata["requires_review"] is True
    assert workflow.metadata["inferred_dependency_count"] == 0
    assert not any("Dependencias provisionales" in o for o in proposal.observations)
    assert [m.source_step for m in proposal.source_map] == [s[0] for s in SOURCE]
    assert [m.page for m in proposal.source_map] == [s[4] for s in SOURCE]
    assert [m.source_excerpt for m in proposal.source_map] == [s[1] for s in SOURCE]
    assert {(e.source, e.target) for e in workflow.edges} == {
        ("inicio", "etapa_1"),
        *((f"etapa_{i}", f"etapa_{i+1}") for i in range(1, 23)),
        ("etapa_23", "fin"),
    }


def test_document_reference_keeps_participant_roles_separate():
    proposal = _compile_source_extraction(_fixture())
    by_number = {m.source_step: m.node_id for m in proposal.source_map}
    nodes = {n.id: n for n in proposal.workflow.nodes}
    assert nodes[by_number["2"]].config["actor_side"] == "CONTRATISTA"
    assert nodes[by_number["8"]].config["actor_side"] == "CONTRATISTA"
    assert nodes[by_number["3"]].config["actor_side"] == "CONTRATANTE"
    assert nodes[by_number["6"]].config["actor_side"] == "CONTRATANTE"
    assert nodes[by_number["12"]].config["actor_side"] == "CONTRATANTE"
    assert nodes[by_number["2.1"]].kind == "NOTIFICATION"
    assert nodes[by_number["8"]].kind == "SIGNATURE"
    assert workflow_is_review_only(proposal)


def workflow_is_review_only(proposal):
    return proposal.workflow.metadata["draft"] is True and all(
        n.config.get("execution_mode") == "MANUAL"
        for n in proposal.workflow.nodes
    )
