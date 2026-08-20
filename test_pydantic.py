from pydantic import BaseModel, field_validator
from typing import List

class Task(BaseModel):
    retry_history: List[str]
    @field_validator("retry_history", mode="before")
    def coerce(cls, v):
        if isinstance(v, dict) and len(v) == 0:
            return []
        return v

try:
    print(Task.model_validate_json('{"retry_history": {}}'))
    print("SUCCESS JSON")
except Exception as e:
    print("FAILED JSON:", e)

try:
    print(Task.model_validate({"retry_history": {}}))
    print("SUCCESS DICT")
except Exception as e:
    print("FAILED DICT:", e)
