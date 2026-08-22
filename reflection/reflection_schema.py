from pydantic import BaseModel


class ReflectionResult(BaseModel):

    passed:bool

    score:float

    issues:list[str]

    recommendation:str