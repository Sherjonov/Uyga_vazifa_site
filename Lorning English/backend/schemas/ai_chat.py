from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ChatIn(BaseModel):
    content: str = Field(default="", max_length=8000)
    image_data: Optional[str] = Field(default=None, max_length=7_000_000)
    file_data: Optional[str] = Field(default=None, max_length=14_000_000)
    file_name: Optional[str] = Field(default=None, max_length=255)
    assignment_id: Optional[int] = None  # qaysi vazifa haqida so'ralayotgani (ixtiyoriy)
    model: Optional[str] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_single_attachment(self):
        attachments = [self.image_data, self.file_data]
        if sum(value is not None for value in attachments) > 1:
            raise ValueError("Only one attachment can be sent per message")
        if self.file_data is not None and not self.file_name:
            raise ValueError("A document filename is required")
        return self


class ChatRename(BaseModel):
    title: str = Field(min_length=1, max_length=120)
