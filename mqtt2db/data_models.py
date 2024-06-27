from pydantic import BaseModel


class EmeterModel(BaseModel):
    name: str
    status: bool
    V: float
    A: float
    W: float
    total_wh: float
