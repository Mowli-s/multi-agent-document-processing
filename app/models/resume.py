from pydantic import BaseModel, Field


class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class Education(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    year: str | None = None


class ResumeData(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    location: str | None = None

    skills: list[str] = Field(default_factory=list)

    experience: list[Experience] = Field(default_factory=list)

    education: list[Education] = Field(default_factory=list)

    summary: str | None = None