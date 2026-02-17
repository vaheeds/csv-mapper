import uuid
import json
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db import models
from app.models.mapping import SavedMapping, SavedMappingList
from app.models.schema_def import PREDEFINED_SCHEMA
from app.services import validator

def _get_db() -> Session:
    return SessionLocal()

def _to_saved_mapping(row: models.Mapping) -> SavedMapping:
    return SavedMapping(
        id=row.id,
        name=row.name,
        schema_name=row.schema_name,
        schema_version=row.schema_version,
        mapping=json.loads(row.mapping_json),
    )

def list_mappings() -> SavedMappingList:
    db = _get_db()
    try:
        rows = db.query(models.Mapping).all()
        items = [_to_saved_mapping(r) for r in rows]
        return SavedMappingList(items=items)
    finally:
        db.close()

def save_mapping(name: str, mapping: Dict[str, str]) -> SavedMapping:
    db = _get_db()
    try:
        # Check if a mapping with this name already exists
        existing_mapping = db.query(models.Mapping).filter(models.Mapping.name == name).first()
        
        if existing_mapping:
            raise ValueError(f"A mapping with the name '{name}' already exists.")

        mapping_id = str(uuid.uuid4())
        row = models.Mapping(
            id=mapping_id,
            name=name,
            schema_name=PREDEFINED_SCHEMA.name,
            schema_version=PREDEFINED_SCHEMA.version,
            mapping_json=json.dumps(mapping),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _to_saved_mapping(row)
    finally:
        db.close()

def get_mapping(mapping_id: str) -> SavedMapping:
    db = _get_db()
    try:
        row = db.query(models.Mapping).filter(models.Mapping.id == mapping_id).first()
        if not row:
            raise KeyError(f"Mapping with id {mapping_id} not found")
        return _to_saved_mapping(row)
    finally:
        db.close()

def save_customer_data(rows: List[Dict[str, Any]]) -> int:
    """
    Saves a list of mapped dictionaries to the CustomerImportData table.
    Returns the number of records saved.
    """
    db = _get_db()
    try:
        customer_objects = []
        load_datetime = datetime.now().isoformat()
        for row in rows:
           
            customer_data = models.CustomerImportData(
                load_datetime=load_datetime,
                customer_id=row.get("customer_id"),
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                email=row.get("email"),
                date_of_birth=row.get("date_of_birth"), 
                website=row.get("website"),
                is_active=row.get("is_active"),
                status=row.get("status"),
                cancel_reason=row.get("cancel_reason"),
                signup_date=row.get("signup_date"),
                last_activity_date=row.get("last_activity_date")
            )
            customer_objects.append(customer_data)
        
        db.add_all(customer_objects)
        db.commit()
        
        return len(customer_objects)
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def transform_row(raw_row: Dict[str, str], mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Converts a raw CSV row into a structured dictionary that matches our internal schema.
    It renames keys and converts data types (strings -> dates/bools) based on the mapping.
    """
    transformed = {}

    # Iterate through every field defined in our strict internal schema
    for schema_field_def in PREDEFINED_SCHEMA.fields:
        schema_key = schema_field_def.name

        # If the user hasn't mapped this schema field to a CSV column, leave it empty
        if schema_key not in mapping:
            transformed[schema_key] = None
            continue

        # Look up which CSV column corresponds to this schema field
        csv_col_name = mapping[schema_key]
        raw_val = raw_row.get(csv_col_name)

        # Convert the raw string value into the correct Python type
        if schema_field_def.type == "date":
            # Helper function handles various date formats (e.g., "2023-01-01", "01/01/23")
            transformed[schema_key] = validator.parse_date(raw_val)
            
        elif schema_field_def.type == "boolean":
            # Helper function handles text like "yes", "true", "1", "on"
            transformed[schema_key] = validator.parse_bool(raw_val)
            
        else:
            # For strings or unknown types, keep the value as-is
            transformed[schema_key] = raw_val

    return transformed

