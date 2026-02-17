import pytest
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, mock_open

from app.api.routes import router
from app.models.mapping import MappingValidationResult

# Initialize the app and attach routes to mock a real server and client.
app = FastAPI()
app.include_router(router)

client = TestClient(app)

# --- Fixtures for Mocking ---

@pytest.fixture
def mock_csv_loader():
    # Replaces 'csv_loader' in the routes file with a fake object (mock).
    with patch("app.api.routes.csv_loader") as mock:
        yield mock

@pytest.fixture
def mock_validator():
    # Replaces the validation logic so we can force tests to pass or fail validation.
    with patch("app.api.routes.validator") as mock:
        yield mock

@pytest.fixture
def mock_mapping_suggester():
    # Replaces the logic that suggests column mappings.
    with patch("app.api.routes.mapping_suggester") as mock:
        yield mock

@pytest.fixture
def mock_mapping_store():
    # Replaces the database storage layer.
    with patch("app.api.routes.mapping_store") as mock:
        yield mock

@pytest.fixture
def mock_transform_row():
    with patch("app.api.routes.transform_row") as mock:
        yield mock

@pytest.fixture
def mock_schema():
    # Replaces the PREDEFINED_SCHEMA constant during testing (only 'id' and 'name' required).
    with patch("app.api.routes.PREDEFINED_SCHEMA", {"required_cols": ["id", "name"]}) as mock:
        yield mock

# --- General Routes ---

def test_get_schema(mock_schema):
    """
    Goal: Verify the /schema endpoint returns the correct JSON structure.
    """
    # 1. Action: Send GET request
    response = client.get("/schema")
    
    # 2. Check: Status should be 200 (OK)
    assert response.status_code == 200
    
    # 3. Check: The returned JSON matches the mock schema we defined in the fixture.
    assert response.json() == {"required_cols": ["id", "name"]}

# --- CSV Upload & Inspection ---

def test_upload_csv_success(mock_csv_loader):
    """
    Goal: Test a successful file upload flow.
    """
    # 1. Setup: Teach the mock how to behave.
    # When the code calls save_uploaded_file, return "file_123" (fake ID).
    mock_csv_loader.save_uploaded_file.return_value = "file_123"
    mock_csv_loader.get_file_path.return_value = "/tmp/file_123.csv"
    mock_csv_loader.detect_header.return_value = True 
    
    # Create a fake file to send
    files = {"file": ("test.csv", b"col1,col2\nval1,val2", "text/csv")}
    
    # 2. Action: Send the file to the endpoint
    response = client.post("/upload", files=files, data={"delimiter": ",", "encoding": "utf-8"})
    
    # 3. Check: Request succeeded
    assert response.status_code == 200
    data = response.json()
    
    # 4. Verify: The API returns the fake ID we told the mock to generate
    assert data["file_id"] == "file_123"
    assert data["has_header"] is True
    
    # 5. Verify: The code actually called our mock function exactly once
    mock_csv_loader.save_uploaded_file.assert_called_once()
    mock_csv_loader.detect_header.assert_called_once()

def test_upload_csv_failure(mock_csv_loader):
    """
    Goal: Ensure the API handles errors gracefully (e.g., bad file format).
    """
    # 1. Setup: Force the mock to crash with a ValueError
    mock_csv_loader.save_uploaded_file.side_effect = ValueError("Invalid format")
    
    files = {"file": ("bad.csv", b"content", "text/csv")}
    
    # 2. Action: Send the request
    response = client.post("/upload", files=files, data={"delimiter": ",", "encoding": "utf-8"})
    
    # 3. Check: The API should catch the error and return 400 (Bad Request), not 500.
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid format"

def test_get_columns(mock_csv_loader):
    """
    Goal: Verify retrieving the list of columns from a file.
    """
    # 1. Setup: Create a fake column object to return
    mock_col = MagicMock()
    mock_col.model_dump.return_value = {"name": "Col1", "index": 0}
    
    # Tell the loader: "When asked to inspect columns, return this list"
    mock_csv_loader.inspect_columns.return_value = [mock_col]
    
    # 2. Action: Request columns for a specific file ID
    response = client.get("/columns?file_id=123&has_header=true")
    
    # 3. Check: The response contains the fake column data
    assert response.status_code == 200
    assert response.json() == {"columns": [{"name": "Col1", "index": 0}]}

def test_get_preview_success(mock_csv_loader):
    """
    Goal: specific test to read the first few lines of a CSV.
    """
    mock_csv_loader.get_file_path.return_value = "/tmp/test.csv"
    
    # We fake the actual python 'open()' command.
    csv_content = "col1,col2\nval1,val2\nval3,val4"
    with patch("builtins.open", mock_open(read_data=csv_content)):
        
        # Action: Ask for a preview limited to 2 rows
        response = client.get("/preview?file_id=123&has_header=true&limit=2")
        
        assert response.status_code == 200
        # Check: The API should skip the header (row 0) and return the data rows
        assert response.json()["rows"] == [["val1", "val2"], ["val3", "val4"]]

# --- Mapping Suggestions & Validation ---

def test_suggest_mapping(mock_csv_loader, mock_mapping_suggester):
    """
    Goal: Test if the API correctly asks the suggester for help.
    """
    # 1. Setup: Fake the column inspection
    mock_col = MagicMock()
    mock_csv_loader.inspect_columns.return_value = [mock_col]
    
    # 2. Setup: Fake the suggestion result
    mock_suggestion = MagicMock()
    mock_suggestion.model_dump.return_value = {"csv_column": "Col1", "schema_field": "id"}
    mock_mapping_suggester.suggest_mappings.return_value = [mock_suggestion]
    
    # 3. Action
    response = client.get("/suggest-mapping?file_id=123")
    
    # 4. Check
    assert response.status_code == 200
    assert response.json()["suggestions"][0]["csv_column"] == "Col1"

def test_validate_mapping_valid(mock_csv_loader, mock_validator):
    """
    Goal: Test the validation endpoint when everything is correct.
    """
    mock_csv_loader.get_file_path.return_value = "/path/to/file"
    
    # 1. Setup: Force structure validation to pass (is_valid=True)
    structural_res = MappingValidationResult(is_valid=True, errors=[])
    mock_validator.validate_mapping_structure.return_value = structural_res
    
    # 2. Setup: Force content validation to pass (is_valid=True)
    content_res = MappingValidationResult(is_valid=True, errors=[])
    mock_validator.validate_csv_rows.return_value = content_res
    
    payload = {
        "file_id": "123",
        "mapping": {"target1": "col1"},
        "has_header": True
    }
    
    # 3. Action
    response = client.post("/validate-mapping", json=payload)
    
    # 4. Check: The API should report the mapping is valid
    assert response.status_code == 200
    assert response.json()["is_valid"] is True

# --- Save Mapping ---

def test_save_mapping_success(mock_mapping_store):
    """
    Goal: Test saving a mapping configuration to the database.
    """
    # 1. Setup: Fake a successful DB save
    mock_mapping_store.save_mapping.return_value = {
        "id": "map_123", 
        "name": "Test Map",
        "mapping": {"target1": "col1"}
    }
    
    form_data = {
        "name": "Test Map",
        "mapping_json": '{"target1": "col1"}' # Input is a JSON string
    }
    
    # 2. Action
    response = client.post("/mapping", data=form_data)
    
    # 3. Check
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "map_123"
    
    # 4. Verify: Ensure the code parsed the JSON string back into a dict before saving
    mock_mapping_store.save_mapping.assert_called_once_with(
        name="Test Map",
        mapping={"target1": "col1"}
    )

def test_save_mapping_duplicate(mock_mapping_store):
    """
    Goal: Test what happens if we try to save a map with a name that already exists.
    """
    # 1. Setup: Make the DB raise an error
    mock_mapping_store.save_mapping.side_effect = ValueError("Name already exists")
    
    form_data = {
        "name": "Test Map",
        "mapping_json": '{"target1": "col1"}'
    }
    
    # 2. Action
    response = client.post("/mapping", data=form_data)
    
    # 3. Check: Expect a 409 Conflict status
    assert response.status_code == 409
    assert "Name already exists" in response.json()["detail"]

def test_save_mapping_invalid_json():
    """
    Goal: Test input validation for bad JSON strings.
    """
    form_data = {
        "name": "Test Map",
        "mapping_json": '{bad json' # Malformed JSON
    }
    response = client.post("/mapping", data=form_data)
    
    # Check: Expect 400 Bad Request
    assert response.status_code == 400
    assert "Invalid mapping_json" in response.json()["detail"]

# --- Ingest Data ---

def test_ingest_data_success(mock_csv_loader, mock_validator, mock_mapping_store, mock_transform_row):
    """
    Goal: Test the full ingestion pipeline.
    This simulates: Inspecting -> Validating -> Reading -> Transforming -> Saving.
    """
    # 1. Setup: Fake column inspection (needed so the code knows what columns exist)
    col_mock = MagicMock()
    col_mock.name = "col1"
    mock_csv_loader.inspect_columns.return_value = [col_mock]
    
    # 2. Setup: Force validation to pass
    structural_res = MappingValidationResult(is_valid=True, errors=[])
    mock_validator.validate_mapping_structure.return_value = structural_res
    
    # 3. Setup: Fake the CSV rows being read
    raw_rows = [{"col1": "val1"}, {"col1": "val2"}]
    mock_csv_loader.get_rows.return_value = raw_rows
    
    # 4. Setup: Fake the row transformation logic
    # We make it return a simple dictionary based on the input
    mock_transform_row.side_effect = lambda row, mapping: {"db_col": row}
    
    # 5. Setup: Fake the DB save returning "2 rows saved"
    mock_mapping_store.save_customer_data.return_value = 2 
    
    form_data = {
        "file_id": "file_123",
        "has_header": "true",
        "mapping_json": '{"db_col": "col1"}'
    }
    
    # Action
    response = client.post("/ingest-data", data=form_data)
    
    # Check
    assert response.status_code == 200
    assert response.json() == 2 # Expecting the count of saved records
    
    # Verifications: Ensure the pipeline steps actually happened
    mock_validator.validate_mapping_structure.assert_called_once()
    mock_csv_loader.get_rows.assert_called_once_with(file_id="file_123", has_header=True)
    assert mock_transform_row.call_count == 2 # Called once per row
    mock_mapping_store.save_customer_data.assert_called_once()

def test_ingest_data_invalid_mapping_structure(mock_csv_loader, mock_validator):
    """
    Goal: Ensure we don't try to save data if the mapping is invalid.
    """
    # 1. Setup: Inspect columns
    col_mock = MagicMock()
    col_mock.name = "col1"
    mock_csv_loader.inspect_columns.return_value = [col_mock]
    
    # 2. Setup: Force validation to FAIL
    structural_res = MappingValidationResult(is_valid=False, errors=["Field mismatch"])
    mock_validator.validate_mapping_structure.return_value = structural_res
    
    form_data = {
        "file_id": "file_123",
        "has_header": "true",
        "mapping_json": '{"db_col": "col1"}'
    }
    
    # Action
    response = client.post("/ingest-data", data=form_data)
    
    # Check: Expect 400 Bad Request
    assert response.status_code == 400
    assert "Cannot save invalid mapping" in response.json()["detail"]

def test_ingest_data_db_error(mock_csv_loader, mock_validator, mock_mapping_store):
    """
    Goal: Test error handling when the database crashes during save.
    """
    # 1. Setup: Happy path for validation and loading
    mock_csv_loader.inspect_columns.return_value = [MagicMock(name="col1")]
    mock_validator.validate_mapping_structure.return_value = MappingValidationResult(is_valid=True, errors=[])
    mock_csv_loader.get_rows.return_value = [{"col1": "val1"}]
    
    # 2. Setup: Force the DB to raise a generic Exception
    mock_mapping_store.save_customer_data.side_effect = Exception("DB Connection Fail")
    
    form_data = {
        "file_id": "file_123",
        "has_header": "true",
        "mapping_json": '{"db_col": "col1"}'
    }
    
    # Action
    response = client.post("/ingest-data", data=form_data)
    
    # Check: Expect 500 Internal Server Error
    assert response.status_code == 500
    assert "Error processing data" in response.json()["detail"]
    assert "DB Connection Fail" in response.json()["detail"]

# --- CRUD Mappings ---

def test_list_mappings(mock_mapping_store):
    """
    Goal: Test listing all saved mappings.
    """
    # Setup: Return an empty list
    mock_mapping_store.list_mappings.return_value = {"items": []}
    
    # Action
    response = client.get("/mappings")
    
    # Check
    assert response.status_code == 200

def test_get_mapping_not_found(mock_mapping_store):
    """
    Goal: Test trying to get a mapping ID that doesn't exist.
    """
    # Setup: Raise KeyError (simulating 'not found' in a dictionary or DB)
    mock_mapping_store.get_mapping.side_effect = KeyError("Not found")
    
    # Action
    response = client.get("/mappings/999")
    
    # Check: Expect 404 Not Found
    assert response.status_code == 404
