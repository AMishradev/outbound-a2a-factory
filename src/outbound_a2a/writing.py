from outbound_a2a.models import EmailDraft, EmailRequest, ResearchBrief


def build_research_brief(request: EmailRequest) -> ResearchBrief:
    """Synthesize only the supplied facts; no invented web research."""
    return ResearchBrief(
        audience=(
            f"{request.recipient_name}, {request.recipient_role} at "
            f"{request.recipient_company}"
        ),
        likely_priority=request.pain_point,
        value_hypothesis=(
            f"{request.offering.capitalize()} could help {request.recipient_company} "
            f"address {request.pain_point}."
        ),
        credible_evidence=request.proof_point,
        personalization_note=(
            f"Connect the {request.recipient_role} remit to the stated pain point; "
            "do not imply facts beyond the supplied brief."
        ),
    )


def build_email(request: EmailRequest, brief: ResearchBrief) -> EmailDraft:
    """Create a deliberately small, inspectable professional email template."""
    subject = f"Idea for {request.recipient_company}'s outbound workflow"
    body = (
        f"Hi {request.recipient_name},\n\n"
        f"Given your role as {request.recipient_role}, I thought this might be "
        f"relevant: {brief.likely_priority.rstrip('.')} . "
        f"{request.sender_company} offers {request.offering}, and "
        f"{brief.credible_evidence.rstrip('.')} .\n\n"
        f"{request.call_to_action}\n\n"
        f"Best,\n{request.sender_name}"
    ).replace(" .", ".")
    return EmailDraft(subject=subject, body=body, research_brief=brief)
