from pydantic import BaseModel, Field

class CaseCreate(BaseModel):
    external_ref: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=240)

class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1)

class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    limit: int = Field(default=5, ge=1, le=20)

class SummaryRequest(BaseModel):
    question: str = Field(min_length=2)
    limit: int = Field(default=6, ge=1, le=20)
