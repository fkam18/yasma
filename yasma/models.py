from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class JobResponse(BaseModel):
    id: int
    status: str
    title: str
    vibe: str
    hints: str
    length: str
    categories: List[str]
    model: str
    use_exif: bool
    exif_data: Optional[str] = None
    story: Optional[str] = None
    images: List[str]
    marked: bool = False
    created_at: datetime
    error_message: Optional[str] = None

class JobList(BaseModel):
    jobs: List[JobResponse]

class PostRequest(BaseModel):
    plugins: List[str]

class PostResponse(BaseModel):
    results: dict

class SettingsDefaults(BaseModel):
    title: str
    vibe: str
    hints: str
    categories: List[str]
    length: str
    use_exif: bool
    model: str
    post_plugins: List[str] = [] 

class SettingsResponse(BaseModel):
    auto_approve: bool
    defaults: SettingsDefaults
    plugins: List[str] = []
    allowed_categories: List[str] = []

class SettingsUpdate(BaseModel):
    auto_approve: Optional[bool] = None

class LogResponse(BaseModel):
    log: List[str]

class ProcessResponse(BaseModel):
    processed: int
    posted: int
    failed: int
