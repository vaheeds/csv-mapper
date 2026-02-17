import pytest
import json
import uuid
from unittest.mock import MagicMock, patch
from app.db import models
from app.services.mapping_store import list_mappings, save_mapping, get_mapping
from app.models.mapping import SavedMapping

# --- Fixtures for Database Mocking ---

@pytest.fixture
def mock_db_session():
    """
    Goal: Simulate a database session because a real database isn't running.
    """
    # We patch where SessionLocal is IMPORTED in mapping_store.py, not where it's defined in database.py
    with patch("app.services.mapping_store.SessionLocal") as mock:
        session = MagicMock()
        mock.return_value = session
        yield session

@pytest.fixture
def mock_predefined_schema():
    """
    Goal: Control the schema version used in tests.
    """
    with patch("app.services.mapping_store.PREDEFINED_SCHEMA") as mock:
        mock.name = "TestSchema"
        mock.version = "1.0"
        yield mock

# --- Tests for Listing Mappings ---

def test_list_mappings_success(mock_db_session):
    """
    Goal: Test retrieving all saved mappings and converting them to the correct output format.
    """
    # 1. Setup: Create fake database rows (objects with attributes like a DB row)
    row1 = MagicMock()
    row1.id = "id_1"
    row1.name = "Map 1"
    row1.schema_name = "SchemaA"
    row1.schema_version = "1.0"
    # The DB stores the mapping as a JSON string, so we mock that string format.
    row1.mapping_json = '{"col1": "field1"}'

    row2 = MagicMock()
    row2.id = "id_2"
    row2.name = "Map 2"
    row2.schema_name = "SchemaA"
    row2.schema_version = "1.0"
    row2.mapping_json = '{"col2": "field2"}'

    # 2. Setup: Tell the mock database what to return when queried.
    # Logic: db_session.query(Model).all() returns our list of rows.
    mock_db_session.query.return_value.all.return_value = [row1, row2]

    # 3. Action: Call the service function
    result = list_mappings()

    # 4. Check: Verify the results were parsed correctly
    assert len(result.items) == 2
    assert result.items[0].id == "id_1"
    # Ensure the JSON string from the DB was parsed back into a dictionary
    assert result.items[0].mapping == {"col1": "field1"}
    assert result.items[1].name == "Map 2"
    
    # 5. Verify: Crucial for DB apps - ensure the connection was closed.
    mock_db_session.close.assert_called_once()

def test_list_mappings_empty(mock_db_session):
    """
    Goal: Verify behavior when the database table is empty.
    """
    # Setup: Return an empty list
    mock_db_session.query.return_value.all.return_value = []

    # Action
    result = list_mappings()

    # Check
    assert len(result.items) == 0
    mock_db_session.close.assert_called_once()

# --- Tests for Saving Mappings ---

def test_save_mapping_success(mock_db_session, mock_predefined_schema):
    """
    Goal: Test the 'Happy Path' for saving a new mapping.
    It verifies that we validate the name, create the object, and commit to the DB.
    """
    # 1. Setup
    name = "New Mapping"
    mapping_dict = {"csv_col": "schema_field"}
    
    # Simulate that the name is available (query returns None, meaning no duplicate found)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # 2. Action
    result = save_mapping(name, mapping_dict)
    
    # 3. Verify Database Interactions
    mock_db_session.add.assert_called_once()    # Staged the new row
    mock_db_session.commit.assert_called_once() # Saved to DB
    mock_db_session.refresh.assert_called_once() # Refreshed to get the ID
    mock_db_session.close.assert_called_once()  # Closed connection
    
    # 4. Verify the Data Sent to DB
    # We grab the arguments passed to 'session.add()' to inspect the object being saved.
    args, _ = mock_db_session.add.call_args
    added_obj = args[0]
    
    assert added_obj.name == name
    assert added_obj.schema_name == "TestSchema"
    assert added_obj.schema_version == "1.0"
    # It should have converted our dict back to a JSON string for storage
    assert json.loads(added_obj.mapping_json) == mapping_dict
    # ID should be generated as a UUID
    assert uuid.UUID(added_obj.id)
    
    # 5. Verify the Function Return Value
    assert isinstance(result, SavedMapping)
    assert result.name == name
    assert result.mapping == mapping_dict

def test_save_mapping_duplicate_name_error(mock_db_session, mock_predefined_schema):
    """
    Goal: Test Business Logic. We do not allow two mappings with the same name.
    """
    name = "Existing Name"
    mapping_dict = {"a": "b"}

    # 1. Setup: Simulate finding an existing row in the DB when checking the name.
    existing_row = models.Mapping(id="123", name=name)
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing_row

    # 2. Action: Expect a ValueError
    with pytest.raises(ValueError) as excinfo:
        save_mapping(name, mapping_dict)
    
    # 3. Check: Error message
    assert f"A mapping with the name '{name}' already exists" in str(excinfo.value)

    # 4. Verify: Ensure we did NOT try to write anything to the DB
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()
    
# --- Tests for Getting Single Mapping ---

def test_get_mapping_success(mock_db_session):
    """
    Goal: Retrieve a single specific mapping by ID.
    """
    target_id = "test_id_123"
    
    # 1. Setup: Create the row we want to 'find'
    mock_row = MagicMock()
    mock_row.id = target_id
    mock_row.name = "Target Map"
    mock_row.schema_name = "Schema"
    mock_row.schema_version = "1"
    mock_row.mapping_json = '{"a": "b"}'
    
    # Logic: db.query().filter().first() returns our row
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_row
    
    # 2. Action
    result = get_mapping(target_id)
    
    # 3. Check
    assert result.id == target_id
    assert result.name == "Target Map"
    assert result.mapping == {"a": "b"}
    mock_db_session.close.assert_called_once()

def test_get_mapping_not_found(mock_db_session):
    """
    Goal: Verify behavior when the ID doesn't exist.
    """
    # Setup: Query returns None (not found)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Action: Expect KeyError (typical pythonic 'not found' error)
    with pytest.raises(KeyError) as excinfo:
        get_mapping("non_existent_id")
    
    assert "Mapping with id non_existent_id not found" in str(excinfo.value)
    mock_db_session.close.assert_called_once()

def test_db_close_on_exception(mock_db_session):
    """
    Goal: Safety Check. 
    Ensure the database connection is closed even if the code crashes midway.
    """
    # Setup: Force the query to crash with a generic Exception
    mock_db_session.query.side_effect = Exception("DB Error")
    
    # Action: Run the function, expecting it to crash
    with pytest.raises(Exception):
        list_mappings()
        
    # Verify: The 'finally' block in the service code should have closed the session.
    mock_db_session.close.assert_called_once()
