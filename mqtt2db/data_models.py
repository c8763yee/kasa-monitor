from pydantic import BaseModel


class EmeterModel(BaseModel):
    name: str
    is_on: bool
    V: float
    A: float
    W: float
    total_wh: float
