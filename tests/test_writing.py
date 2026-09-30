from outbound_a2a.cli import example_request
from outbound_a2a.writing import build_email, build_research_brief


def test_pipeline_uses_supplied_facts() -> None:
    request = example_request()
    brief = build_research_brief(request)
    draft = build_email(request, brief)

    assert request.recipient_company in draft.subject
    assert request.recipient_name in draft.body
    assert request.proof_point in draft.body
    assert request.call_to_action in draft.body
    assert draft.research_brief == brief


def test_research_brief_warns_against_invention() -> None:
    brief = build_research_brief(example_request())
    assert "do not imply facts" in brief.personalization_note
