import pytest
from app.models.schema_def import PredefinedSchema, SchemaField, CrossFieldRule

# --- Test Field Initialization ---

def test_schema_field_initialization():
    """
    Goal: Verify that a single SchemaField object (representing one column in the DB) 
    is created correctly with the properties we give it.
    """
    # 1. Action: Create a new field
    field = SchemaField(name="test", type="string", required=True)

    # 2. Check: Properties match inputs
    assert field.name == "test"
    assert field.required is True

# --- Test Schema Helper Methods ---

def test_predefined_schema_helper_methods():
    """
    Goal: Verify the helper methods on the main PredefinedSchema object.
    These helpers are used throughout the app to quickly look up field info.
    """
    # 1. Setup: Create a schema with one required field and one optional field
    fields = [
        SchemaField(name="id", type="integer", required=True),
        SchemaField(name="optional_desc", type="string", required=False),
    ]
    schema = PredefinedSchema(name="TestSchema", version="1.0", fields=fields)

    # 2. Test: required_field_names()
    # Logic: This method should return ONLY the names of fields marked required=True
    required = schema.required_field_names()
    
    assert "id" in required             # Should be there
    assert "optional_desc" not in required # Should NOT be there
    assert len(required) == 1

    # 3. Test: field_by_name()
    # Logic: This allows us to get the full field object just by knowing its name string
    
    # Case A: Field exists
    f = schema.field_by_name("id")
    assert f is not None
    assert f.type == "integer"

    # Case B: Field does not exist
    f_missing = schema.field_by_name("non_existent")
    assert f_missing is None

# --- Test Rules ---

def test_cross_field_rule_initialization():
    """
    Goal: Verify that CrossFieldRule objects (used for complex validation logic, 
    like 'StartDate must be before EndDate') are initialized correctly.
    """
    # 1. Action: Create a rule
    rule = CrossFieldRule(
        name="test_rule",
        rule_type="date_order",
        field_a="start_date",
        field_b="end_date"
    )

    # 2. Check: Properties are set correctly
    assert rule.name == "test_rule"
    assert rule.field_b == "end_date"
