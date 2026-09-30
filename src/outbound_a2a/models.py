from pydantic import BaseModel, ConfigDict, Field


class EmailRequest(BaseModel):
    """Structured input accepted by the Draft Agent."""

    model_config = ConfigDict(extra="forbid")

    sender_name: str = Field(min_length=1, examples=["Maya"])
    sender_company: str = Field(min_length=1, examples=["Northstar"])
    recipient_name: str = Field(min_length=1, examples=["Jordan"])
    recipient_role: str = Field(min_length=1, examples=["VP of Sales"])
    recipient_company: str = Field(min_length=1, examples=["Acme"])
    offering: str = Field(min_length=1, examples=["an outbound workflow platform"])
    pain_point: str = Field(
        min_length=1, examples=["reps spend too much time drafting follow-ups"]
    )
    proof_point: str = Field(
        min_length=1, examples=["teams cut drafting time by 40%"]
    )
    call_to_action: str = Field(
        default="Would a 15-minute conversation next week be useful?",
        min_length=1,
    )
    tone: str = Field(default="concise and professional", min_length=1)


class ResearchBrief(BaseModel):
    """The structured artifact returned by the Research Agent."""

    model_config = ConfigDict(extra="forbid")

    audience: str
    likely_priority: str
    value_hypothesis: str
    credible_evidence: str
    personalization_note: str


class EmailDraft(BaseModel):
    """The final artifact returned by the Draft Agent."""

    subject: str
    body: str
    research_brief: ResearchBrief
