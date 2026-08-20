from pydantic import BaseModel, Field


class ContractData(BaseModel):
    parties: list[str] = Field(default_factory=list)

    effective_date: str | None = None
    expiration_date: str | None = None

    key_clauses: list[str] = Field(default_factory=list)

    signatures_present: bool = False

    summary: str | None = None