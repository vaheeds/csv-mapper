import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Dict, Optional, List
from app.models.errors import ErrorResponse
from app.models.mapping import (
    UploadMetadata,
    MappingRequest,
    MappingValidationResult,
)
from app.models.schema_def import PREDEFINED_SCHEMA
from app.services import csv_loader, mapping_suggester, validator, mapping_store
from app.services import validator
from app.services.mapping_store import transform_row

router = APIRouter()

@router.get("/schema")
async def get_schema():
    return PREDEFINED_SCHEMA

@router.post(
    "/upload",
    response_model=UploadMetadata,
    responses={400: {"model": ErrorResponse}},
)
async def upload_csv(
    file: UploadFile = File(...),
    delimiter: str = Form(","),
    encoding: str = Form("utf-8"),
):
    try:
        file_id = csv_loader.save_uploaded_file(file)
        
        # Get the full path to the saved file to inspect it
        file_path = csv_loader.get_file_path(file_id)
        
        # Automate header detection
        detected_header = csv_loader.detect_header(file_path, encoding=encoding)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return UploadMetadata(
        file_id=file_id,
        original_filename=file.filename,
        has_header=detected_header, 
        delimiter=delimiter,
        encoding=encoding,
    )

@router.get("/columns")
async def get_columns(
    file_id: str = Query(...),
    has_header: bool = Query(True),
    delimiter: str = Query(","),
    encoding: str = Query("utf-8"),
):
    cols = csv_loader.inspect_columns(
        file_id=file_id,
        has_header=has_header,
        delimiter=delimiter,
        encoding=encoding,
    )
    return {"columns": [c.model_dump() for c in cols]}

@router.get("/suggest-mapping")
async def suggest_mapping(
    file_id: str,
    has_header: bool = True,
    delimiter: str = ",",
    encoding: str = "utf-8",
):
    cols = csv_loader.inspect_columns(
        file_id=file_id,
        has_header=has_header,
        delimiter=delimiter,
        encoding=encoding,
    )
    suggestions = mapping_suggester.suggest_mappings(cols, PREDEFINED_SCHEMA)
    return {"suggestions": [s.model_dump() for s in suggestions]}

@router.get("/preview")
async def get_preview(
    file_id: str,
    has_header: bool = True,
    limit: int = 5,
):
    """
    Returns the first N rows of the CSV file.
    """
    try:
        path = csv_loader.get_file_path(file_id)

        import csv
        
        rows = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
                        
            all_rows = list(reader)
            
            start_index = 1 if has_header else 0 # Skip header row if present
            data_rows = all_rows[start_index : start_index + limit]
            
            return {"rows": data_rows}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")

@router.post(
    "/validate-mapping",
    response_model=MappingValidationResult,
    responses={400: {"model": ErrorResponse}},
)
async def validate_mapping(request: MappingRequest):
    path = csv_loader.get_file_path(request.file_id)

    # Determine available columns
    cols = csv_loader.inspect_columns(
        file_id=request.file_id,
        has_header=request.has_header,
    )
    available = [c.name for c in cols]

    # 1) structural validation
    structural = validator.validate_mapping_structure(
        mapping=request.mapping,
        schema=PREDEFINED_SCHEMA,
        available_columns=available,
    )

    if not structural.is_valid:
        return structural

    # 2) content validation on sample rows
    content = validator.validate_csv_rows(
        file_path=path,
        has_header=request.has_header,
        delimiter=",",
        mapping=request.mapping,
        schema=PREDEFINED_SCHEMA,
        max_rows=1000,
    )

    # merge messages
    all_errors = structural.errors + content.errors

    return MappingValidationResult(
        is_valid=len(all_errors) == 0,
        errors=all_errors,
    )

@router.post("/mapping")
async def save_mapping(
    name: str = Form(...),
    mapping_json: str = Form(...),
):
    import json
    try:
        mapping: Dict[str, str] = json.loads(mapping_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid mapping_json payload")

    try:      
        # Save the Mapping Configuration
        saved_mapping = mapping_store.save_mapping(name=name, mapping=mapping)        
        return saved_mapping
    except ValueError as e:
        # Raise error for duplicate mapping name
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        # Generic server error during processing
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

@router.post("/ingest-data")
async def ingest_data(
    file_id: str = Form(...),
    has_header: bool = Form(True),
    mapping_json: str = Form(...),
):
    import json
    try:
        mapping: Dict[str, str] = json.loads(mapping_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid mapping_json payload")

    # 1. Validate the Mapping Logic 
    cols = csv_loader.inspect_columns(file_id=file_id, has_header=has_header)
    available = [c.name for c in cols]
    
    result = validator.validate_mapping_structure(
        mapping=mapping,
        schema=PREDEFINED_SCHEMA,
        available_columns=available,
    )

    if not result.is_valid:
        raise HTTPException(
            status_code=400,
            detail="Cannot save invalid mapping: " + "; ".join(result.errors),
        )

    try:
        # 2. Load the actual CSV content
        raw_rows = csv_loader.get_rows(file_id=file_id, has_header=has_header) 

        # 3. Transform the data
        transformed_data = []
        for row in raw_rows:
            clean_record = transform_row(row, mapping)
            transformed_data.append(clean_record)
               
        # 4. Save the Customer Data
        records_count = mapping_store.save_customer_data(transformed_data)

        return records_count

    except ValueError as e:
        # Raise error for duplicate mapping name
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        # Generic server error during processing
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")
        
@router.get("/mappings")
async def list_mappings():
    return mapping_store.list_mappings()

@router.get("/mappings/{mapping_id}")
async def get_mapping(mapping_id: str):
    try:
        return mapping_store.get_mapping(mapping_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
