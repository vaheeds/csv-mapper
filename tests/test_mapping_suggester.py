import pytest
from unittest.mock import MagicMock
from app.services.mapping_suggester import (
    suggest_mappings, 
    analyze_content_match, 
    _calculate_name_similarity, 
    normalize_name
)
from app.models.mapping import CsvColumn
from app.models.schema_def import PredefinedSchema, SchemaField

# --- Tests for Helper Functions ---

def test_normalize_name():
    """
    Goal: Ensure column names are cleaned up before comparison.
    """
    assert normalize_name(" First Name ") == "first name" # Trim spaces, lower case
    assert normalize_name("User_ID") == "user id"         # Replace underscores
    assert normalize_name("E-mail Address!") == "e mail address" # Remove punctuation

def test_calculate_name_similarity():
    """
    Goal: Test the logic that compares string similarity.
    Does column 'A' look like column 'B'?
    """
    # Exact match = 100% score (1.0)
    assert _calculate_name_similarity("email", "email") == 1.0
    
    # Partial match: "customer_email" contains "email", so it's a strong match (0.8)
    assert _calculate_name_similarity("customer_email", "email") == 0.8
    
    # Reverse partial: "email" is inside "customer_email", slightly less weight (0.6)
    assert _calculate_name_similarity("email", "customer_email") == 0.6
    
    # No similarity = 0% score (0.0)
    assert _calculate_name_similarity("phone", "email") == 0.0

def test_analyze_content_match_emails():
    """
    Goal: Test if the system can recognize emails by looking at the data rows
    (regex matching), ignoring the column name.
    """
    samples = ["test@example.com", "invalid-email", "hello@world.co"]
    
    # Action: Check against 'email' regex pattern
    score = analyze_content_match(samples, "email")
    
    # Check: 2 out of 3 samples are valid emails, so score is 0.66...
    assert score == 2/3

def test_analyze_content_match_dates():
    """
    Goal: Test recognition of date formats.
    """
    samples = ["2023-01-01", "01/01/2023", "not a date"]
    
    # Action: Check against 'birth_date' regex pattern
    score = analyze_content_match(samples, "birth_date")
    
    # Check: 2 out of 3 match
    assert score == 2/3

def test_analyze_content_match_integers():
    """
    Goal: Test recognition of whole numbers.
    """
    samples = ["123", "456", "7.5", "abc"]
    
    # Action: Check against 'quantity' pattern (expecting integers)
    score = analyze_content_match(samples, "quantity")
    
    # Check: "123" and "456" match. "7.5" is a float, "abc" is text. So 2/4 match.
    assert score == 0.5

def test_analyze_content_match_no_samples():
    """
    Goal: Ensure empty data doesn't crash the math (division by zero).
    """
    assert analyze_content_match([], "email") == 0.0

# --- Tests for Main Logic ---

@pytest.fixture
def mock_schema():
    """
    Goal: Define the 'Target' schema we are trying to map TO.
    """
    return PredefinedSchema(
        name="Test",
        version="1",
        fields=[
            SchemaField(name="email", type="string"),
            SchemaField(name="age", type="integer"),
        ]
    )

def test_suggest_mappings_exact_match(mock_schema):
    """
    Goal: Test the easiest case - the CSV column name exactly matches the database field.
    """
    columns = [
        CsvColumn(name="email", index=0, sample_values=["a@b.com"]),
        CsvColumn(name="random", index=1, sample_values=["xyz"])
    ]
    
    # Action: Run suggestion engine
    suggestions = suggest_mappings(columns, mock_schema)
    
    # Check
    assert len(suggestions) == 1
    # It matched CSV 'email' to Schema 'email'
    assert suggestions[0].schema_field == "email"
    assert suggestions[0].csv_column == "email"
    assert suggestions[0].confidence == 1.0

def test_suggest_mappings_content_match(mock_schema):
    """
    Goal: Test the 'Smart' matching. 
    The column is named "Column 1" (useless name), but the data inside is clearly email addresses.
    The system should look at the sample_values and guess 'email'.
    """
    columns = [
        CsvColumn(name="Column 1", index=0, sample_values=["test@example.com", "user@domain.com"]),
    ]
    
    suggestions = suggest_mappings(columns, mock_schema)
    
    assert len(suggestions) == 1
    assert suggestions[0].schema_field == "email"
    assert suggestions[0].csv_column == "Column 1"
    # Score should be very high because 100% of samples matched the email regex
    assert suggestions[0].confidence >= 0.9

def test_suggest_mappings_ambiguous(mock_schema):
    """
    Goal: Ensure we don't return garbage suggestions.
    If the column ("City") matches nothing in our schema (only email/age), return nothing.
    """
    columns = [
        CsvColumn(name="City", index=0, sample_values=["London", "Paris"]),
    ]
    
    suggestions = suggest_mappings(columns, mock_schema)
    
    # Should find 0 matches
    assert len(suggestions) == 0
