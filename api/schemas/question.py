from pydantic import BaseModel


class SolutionStep(BaseModel):
    description: str
    expression: str


class QuestionCreate(BaseModel):
    subject_name: str
    question_text: str
    solution_steps: list[SolutionStep]
    visual_path: str | None = None


class QuestionResponse(BaseModel):
    id: int
    subject_name: str
    question_text: str
    solution_steps: list[SolutionStep]
    visual_path: str | None

    model_config = {"from_attributes": True}
