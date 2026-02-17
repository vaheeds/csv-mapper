import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from datetime import date

from app.services.validator import (
    validate_mapping_structure,
    validate_csv_rows,
    _validate_field_values,
    _apply_cross_field_rules,
    parse_date
)
from app.models.schema_def import PredefinedSchema, SchemaField, CrossFieldRule

# --- Fixtures ---

@pytest.fixture
def basic_schema():
    """
    Goal: Create a sample schema to use across multiple tests.
    It includes:
        - id: must be an integer
        - email: must be a string matching a regex pattern
        - age: must be an integer between 18 and 100
        - start_date: must be a valid date
    """
    return PredefinedSchema(
        name="Test",
        version="1",
        fields=[
            SchemaField(name="id", type="integer", required=True),
            SchemaField(name="email", type="string", required=True, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),
            SchemaField(name="age", type="integer", min_value=18, max_value=100),
            SchemaField(name="start_date", type="date"),
        ]
    )

# --- Structural Validation Tests ---
# These tests check if the mapping *definition* is valid and did all the required fields mapped?,
# without looking at the actual data inside the CSV yet.

def test_validate_mapping_structure_success(basic_schema):
    """
    Goal: Verify a valid mapping.
    We map 'id' and 'email' (required) to columns that exist.
    """
    mapping = {"id": "col_id", "email": "col_email"}
    available_cols = ["col_id", "col_email", "col_age"]
    
    result = validate_mapping_structure(mapping, basic_schema, available_cols)
    
    # Check: No errors expected
    assert result.is_valid is True
    assert len(result.errors) == 0

def test_validate_mapping_structure_missing_required(basic_schema):
    """
    Goal: Verify that missing a required field (email) triggers an error.
    """
    mapping = {"id": "col_id"} # 'email' is missing
    available_cols = ["col_id"]
    
    result = validate_mapping_structure(mapping, basic_schema, available_cols)
    
    # Check: Invalid status and specific error message
    assert result.is_valid is False
    assert "Required field 'email' is not mapped" in result.errors[0]

def test_validate_mapping_structure_missing_column(basic_schema):
    """
    Goal: Verify that mapping to a non-existent CSV column triggers an error.
    (e.g., User says "Map email to col_ghost", but col_ghost isn't in the CSV).
    """
    mapping = {"id": "col_id", "email": "col_ghost"}
    available_cols = ["col_id"] # 'col_ghost' is NOT here
    
    result = validate_mapping_structure(mapping, basic_schema, available_cols)
    
    # Check
    assert result.is_valid is False
    assert "mapped to missing CSV column 'col_ghost'" in result.errors[0]

# --- Value Validation Tests (_validate_field_values) ---
# These tests look at the actual data (rows) to ensure they match the rules.

def test_validate_field_values_integer_constraints():
    """
    Goal: Test min/max and type constraints for integers. 
    """

    # Example rule: Age must be 18-20.
    field = SchemaField(name="age", type="integer", min_value=18, max_value=20)
    
    # Input data:
    series = pd.Series(["19", "17", "21", "abc"])
    errors = []
    
    # Action: Run validation on this column
    _validate_field_values(field, "csv_age", series, errors)
    
    # Check: Should find type error ("abc")
    assert any("cannot be parsed as integer" in e for e in errors)
    
    # Setup Check 2: Test pure bounds logic with clean numbers
    errors = []
    series_clean = pd.Series(["17", "21"])
    _validate_field_values(field, "csv_age", series_clean, errors)
    
    # Check: Should find range errors
    assert any("values below 18" in e for e in errors)
    assert any("values above 20" in e for e in errors)

def test_validate_field_values_regex():
    """
    Goal: Test regex pattern matching (e.g., ensuring a code is 3 uppercase letters).
    """
    field = SchemaField(name="code", type="string", pattern=r"^[A-Z]{3}$")
    
    # "ABC": OK
    # "def": Fail (lowercase)
    # "123": Fail (numbers)
    series = pd.Series(["ABC", "def", "123"]) 
    errors = []
    
    _validate_field_values(field, "csv_code", series, errors)
    
    # Check
    assert any("do not match required pattern" in e for e in errors)

def test_validate_field_values_date():
    """
    Goal: Test date parsing logic.
    """
    field = SchemaField(name="dob", type="date")
    series = pd.Series(["2020-01-01", "invalid-date"])
    errors = []
    
    _validate_field_values(field, "csv_dob", series, errors)
    
    # Check: Should complain about "invalid-date"
    assert any("invalid date value" in e for e in errors)

# --- Cross Field Rules Tests ---
# These tests check rules that compare TWO columns (e.g., Start Date vs End Date).

def test_cross_field_not_future():
    """
    Goal: Test the 'not_future' rule.
    Dates cannot be in the future relative to today.
    """
    # 1. Setup rule
    rule = CrossFieldRule(name="rule1", rule_type="not_future", field_a="event_date")
    field = SchemaField(name="event_date", type="date")
    schema = PredefinedSchema(name="S", version="1", fields=[field], cross_field_rules=[rule])
    
    # 2. Setup data: 3000-01-01 is in the future
    df = pd.DataFrame({"col_date": ["2020-01-01", "3000-01-01"]})
    mapping = {"event_date": "col_date"}
    errors = []
    
    # 3. Action
    _apply_cross_field_rules(df, mapping, schema, errors)
    
    # 4. Check
    assert any("in the future" in e for e in errors)

def test_cross_field_date_order():
    """
    Goal: Test logical ordering.
    Start Date must be <= End Date.
    """
    # 1. Setup rule: 'start' before 'end'
    rule = CrossFieldRule(
        name="rule2", rule_type="date_order", field_a="start", field_b="end"
    )
    f1 = SchemaField(name="start", type="date")
    f2 = SchemaField(name="end", type="date")
    schema = PredefinedSchema(name="S", version="1", fields=[f1, f2], cross_field_rules=[rule])
    
    # 2. Setup data
    # Row 1: Jan 1 -> Jan 5 (Valid)
    # Row 2: Feb 1 -> Jan 1 (Invalid: Start is after End)
    df = pd.DataFrame({
        "c_start": ["2023-01-01", "2023-02-01"],
        "c_end":   ["2023-01-05", "2023-01-01"] 
    })
    mapping = {"start": "c_start", "end": "c_end"}
    errors = []
    
    # 3. Action
    _apply_cross_field_rules(df, mapping, schema, errors)
    
    # 4. Check
    assert any("should be on or before" in e for e in errors)

# --- Integration / Main Entry Point Test ---

def test_validate_csv_rows_integration(basic_schema):
    """
    Goal: Test the main validation function that ties everything together.
    It reads the CSV, validates structure, and validates values.
    """
    # 1. Setup: Fake the CSV file reading using pandas
    csv_data = pd.DataFrame({
        "col_id": [1, 2],
        "col_email": ["a@b.com", "c@d.com"],
        "col_age": [20, 25],
        "col_date": ["2023-01-01", "2023-01-02"]
    })
    
    # Patch read_csv so we don't need a real file
    with patch("pandas.read_csv", return_value=csv_data):
        mapping = {
            "id": "col_id",
            "email": "col_email", 
            "age": "col_age",
            "start_date": "col_date"
        }
        
        # 2. Action
        result = validate_csv_rows(
            file_path="dummy.csv", 
            has_header=True, 
            delimiter=",", 
            mapping=mapping, 
            schema=basic_schema
        )
        
        # 3. Check: Everything is perfect
        assert result.is_valid is True
        assert len(result.errors) == 0

def test_validate_csv_rows_fail(basic_schema):
    """
    Goal: Test integration when data is bad.
    """
    # Setup: Row has age 10 (Schema minimum is 18)
    csv_data = pd.DataFrame({
        "col_id": [1],
        "col_email": ["a@b.com"],
        "col_age": [10], 
        "col_date": ["2023-01-01"]
    })
    
    with patch("pandas.read_csv", return_value=csv_data):
        mapping = {
            "id": "col_id",
            "email": "col_email", 
            "age": "col_age",
            "start_date": "col_date"
        }
        
        # Action
        result = validate_csv_rows(
            "dummy.csv", True, ",", mapping, basic_schema
        )
        
        # Check: Should fail validation
        assert result.is_valid is False
        assert any("values below 18" in e for e in result.errors)
