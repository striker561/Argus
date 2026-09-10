from pydantic import BaseModel


class StatusData(BaseModel):
    status: str
