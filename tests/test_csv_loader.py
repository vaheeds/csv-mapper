import pytest
import os
import csv
from unittest.mock import MagicMock, patch, mock_open

# importing the specific functions of file I/O and CSV parsing.
from app.services.csv_loader import (
    save_uploaded_file, 
    get_file_path, 
    detect_header, 
    inspect_columns
)

# --- Fixtures ---

@pytest.fixture
def mock_settings():
    """
    Goal: Mock the application settings.
    """
    with patch("app.services.csv_loader.settings") as mock:
        mock.UPLOAD_DIR = "/tmp/uploads"
        mock.MAX_UPLOAD_SIZE_MB = 1  # Set small limit for testing logic
        yield mock

@pytest.fixture
def mock_upload_file():
    """
    Goal: Simulate the 'UploadFile' object that FastAPI provides.
    """
    file_mock = MagicMock()
    # verify the code reads the file in chunks (iterative reading):
    # 1st call: returns b"chunk1"
    # 2nd call: returns b"chunk2"
    # 3rd call: returns b"" (empty bytes indicate End of File)
    file_mock.file.read.side_effect = [b"chunk1", b"chunk2", b""]
    return file_mock

# --- Tests for save_uploaded_file ---

def test_save_uploaded_file_success(mock_settings, mock_upload_file):
    """
    Goal: Verify we can save a file stream to disk correctly.
    """
    # 1. Setup: Fake the 'open' function so we don't write to the real disk.
    with patch("builtins.open", mock_open()) as mocked_file:
        # 2. Setup: Freeze the UUID generation so the filename is predictable ("file-123").
        with patch("uuid.uuid4", return_value="file-123"):
            
            # 3. Action: Call the function
            file_id = save_uploaded_file(mock_upload_file)
            
            # 4. Check: It returned the ID we expected
            assert file_id == "file-123"
            
            # 5. Verify: Did it try to open the correct file path in 'write binary' (wb) mode?
            mocked_file.assert_called_with("/tmp/uploads\\file-123.csv", "wb")
            
            # 6. Verify: Did it actually write our data chunks to that file?
            handle = mocked_file()
            handle.write.assert_any_call(b"chunk1")
            handle.write.assert_any_call(b"chunk2")

def test_save_uploaded_file_too_large(mock_settings):
    """
    Goal: Ensure the upload limit works.
    """
    # Setup: Create a fake chunk that is slightly larger than the 1MB limit we set in the fixture.
    large_chunk = b"x" * (1024 * 1024 + 1) # 1MB + 1 byte
    
    file_mock = MagicMock()
    file_mock.file.read.side_effect = [large_chunk, b""]
    
    # We patch 'os.remove' to verify the cleanup code runs
    with patch("builtins.open", mock_open()):
        with patch("os.remove") as mock_remove:
            
            # Action: Expect a ValueError to be raised
            with pytest.raises(ValueError) as excinfo:
                save_uploaded_file(file_mock)
            
            # Check: Error message matches
            assert "File too large" in str(excinfo.value)
            
            # Verify: The code attempted to delete the partially written file
            mock_remove.assert_called_once()

# --- Tests for get_file_path ---

def test_get_file_path_exists(mock_settings):
    """
    Goal: Verify logic for retrieving a file path when the file exists.
    """
    # Force os.path.exists to confirm file exists
    with patch("os.path.exists", return_value=True):
        path = get_file_path("123")
        assert path == "/tmp/uploads\\123.csv"

def test_get_file_path_not_found(mock_settings):
    """
    Goal: Verify logic when the file is missing.
    """
    # Force os.path.exists to say no file exists
    with patch("os.path.exists", return_value=False):
        # Expect a FileNotFoundError
        with pytest.raises(FileNotFoundError):
            get_file_path("123")

# --- Tests for detect_header ---

def test_detect_header_true(mock_settings):
    """
    Goal: Test if the code correctly identifies a CSV header.
    """
    # Sample data that clearly has headers (Strings, then Integers)
    csv_content = "Name,Age\nAlice,30\nBob,25"
    
    with patch("os.path.exists", return_value=True):
        # Provide the fake file content
        with patch("builtins.open", mock_open(read_data=csv_content)):
            
            # Action
            # Using "dummy_path" because the path doesn't matter.
            result = detect_header("dummy_path")
            
            # Check
            assert result is True

def test_detect_header_sniffer_error(mock_settings):
    """
    Goal: Edge case. If the CSV is weird (e.g. just a list of numbers) and the
    Python `csv.Sniffer` fails, our code should default to True (safe fallback).
    """
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="1\n2\n3")):
            # Force the Sniffer to raise a csv.Error (simulating "I can't tell what this is")
            with patch("csv.Sniffer") as mock_sniffer:
                mock_sniffer.return_value.has_header.side_effect = csv.Error
                
                result = detect_header("dummy_path")
                
                # Check: It defaulted to True
                assert result is True

# --- Tests for inspect_columns ---

def test_inspect_columns_with_header(mock_settings):
    """
    Goal: Verify we can extract column info when headers exist.
    """
    csv_content = "Name,Age\nAlice,30\nBob,25"
    
    # Mocking necessary file path and file reading operations
    with patch("app.services.csv_loader.get_file_path", return_value="/tmp/uploads/123.csv"):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=csv_content)):
                
                # Action: Inspect with header=True
                columns = inspect_columns("123", has_header=True)
                
                assert len(columns) == 2
                
                # Verify Column 1: Should take name from header row
                assert columns[0].name == "Name"
                assert columns[0].index == 0
                assert columns[0].sample_values == ["Alice", "Bob"] # Data rows only
                
                # Verify Column 2
                assert columns[1].name == "Age"
                assert columns[1].index == 1
                assert columns[1].sample_values == ["30", "25"]

def test_inspect_columns_no_header(mock_settings):
    """
    Goal: Verify behavior when there are NO headers.
    The system should auto-generate names (Column 1, Column 2) and treat row 0 as data.
    """
    csv_content = "Alice,30\nBob,25"
    
    with patch("app.services.csv_loader.get_file_path", return_value="/tmp/uploads/123.csv"):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=csv_content)):
                
                # Action: Inspect with header=False
                columns = inspect_columns("123", has_header=False)
                
                assert len(columns) == 2
                
                # Check: Auto-generated name
                assert columns[0].name == "Column 1"
                # Check: The very first row ("Alice") is included in the data samples
                assert columns[0].sample_values[0] == "Alice" 
                
                assert columns[1].name == "Column 2"
                assert columns[1].sample_values[0] == "30"

def test_inspect_columns_empty_file(mock_settings):
    """
    Goal: Ensure empty files result in an empty list, not a crash.
    """
    with patch("app.services.csv_loader.get_file_path", return_value="/tmp/uploads/123.csv"):
        with patch("os.path.exists", return_value=True):
            # Empty content
            with patch("builtins.open", mock_open(read_data="")):
                
                columns = inspect_columns("123", has_header=True)
                assert columns == []

def test_inspect_columns_file_not_found(mock_settings):
    """
    Goal: Ensure we validate the file existence before trying to read it.
    """
    with patch("app.services.csv_loader.get_file_path", return_value="/tmp/uploads/missing.csv"):
        # Force existence check to return False
        with patch("os.path.exists", return_value=False):
            
            with pytest.raises(ValueError, match="File not found"):
                inspect_columns("missing", has_header=True)

def test_inspect_columns_ragged_rows(mock_settings):
    """
    Goal: Test a CSV where some rows column-count, are shorter than others.
    Example: 
    Row 1: Col1, Col2
    Row 2: Val1, Val2
    Row 3: Val3        <-- Missing value for Col2
    """
    csv_content = "Col1,Col2\nVal1,Val2\nVal3" 
    
    with patch("app.services.csv_loader.get_file_path", return_value="/tmp/uploads/123.csv"):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=csv_content)):
                
                columns = inspect_columns("123", has_header=True)
                
                # Find Col2
                col2 = next(c for c in columns if c.name == "Col2")
                
                # Check: It should only have 1 sample ("Val2") because the last row didn't have a 2nd column.
                # The code should skip missing indices instead of crashing.
                assert col2.sample_values == ["Val2"]
