from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from .schema_def import PredefinedSchema, PREDEFINED_SCHEMA

class UploadMetadata(BaseModel):
    file_id: str
    original_filename: str
    has_header: bool 
    delimiter: str = ","
    encoding: str = "utf-8"

class CsvColumn(BaseModel):
    name: str
    index: int
    sample_values: List[str] = Field(default_factory=list)

class MappingSuggestion(BaseModel):
    csv_column: str
    schema_field: Optional[str]  # None if no confident suggestion
    confidence: float

class MappingRequest(BaseModel):
    file_id: str
    has_header: bool
    mapping: Dict[str, str]  # schema_field_name -> csv_column_name

class MappingValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)

class SavedMapping(BaseModel):
    id: str
    name: str
    schema_name: str
    schema_version: str
    mapping: Dict[str, str]  # schema_field_name -> csv_column_name

class SavedMappingList(BaseModel):
    items: List[SavedMapping]

def get_current_schema() -> PredefinedSchema:
    return PREDEFINED_SCHEMA
