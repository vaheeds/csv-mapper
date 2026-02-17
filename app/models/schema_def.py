from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

FieldType = Literal["string", "integer", "float", "boolean", "date", "datetime"]

class SchemaField(BaseModel):
    name: str
    type: FieldType
    required: bool = False
    description: Optional[str] = None
    allowed_values: Optional[List[str]] = None  # For enums

    # --- validation constraints ---
    # String-specific
    pattern: Optional[str] = None             # regex (e.g. for email)
    min_length: Optional[int] = None
    max_length: Optional[int] = None

    # Numeric-specific
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    # Date / datetime-specific (ISO format: "YYYY-MM-DD", "YYYY-MM-DDThh:mm:ss")
    min_date: Optional[str] = None
    max_date: Optional[str] = None

class CrossFieldRule(BaseModel):
    """
    Defines cross-field validations referencing schema field names.
    `rule_type` is a simple indicator implemented manually in validator.py.
    """
    name: str
    rule_type: Literal[
        "date_order",         # field_a <= field_b
        "not_future",         # field_a <= today
        "conditional_required" # for dependent fields, if field_a has given value(s), then field_b required
    ]
    field_a: str
    field_b: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

class PredefinedSchema(BaseModel):
    name: str
    version: str
    fields: List[SchemaField]
    cross_field_rules: List[CrossFieldRule] = Field(default_factory=list)

    def required_field_names(self) -> List[str]:
        return [f.name for f in self.fields if f.required]

    def field_by_name(self, name: str) -> Optional[SchemaField]:
        return next((f for f in self.fields if f.name == name), None)

# Customer schema with some constraints
PREDEFINED_SCHEMA = PredefinedSchema(
    name="CustomerImport",
    version="1.0",
    fields=[
        SchemaField(
            name="customer_id",
            type="string",
            required=True,
            description="Unique customer ID",
            min_length=1,
            max_length=64,
        ),
        SchemaField(
            name="first_name",
            type="string",
            required=True,
            min_length=1,
            max_length=100,
        ),
        SchemaField(
            name="last_name",
            type="string",
            required=True,
            min_length=1,
            max_length=100,
        ),
        SchemaField(
            name="email",
            type="string",
            required=True,
            pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            max_length=255,
        ),
        SchemaField(
            name="date_of_birth",
            type="date",
            required=False,
            # cannot be in the future (handled via cross-field / not_future rule)
            min_date="1900-01-01",
        ),
        SchemaField(
            name="website",
            type="string",
            required=False,
            pattern=r"^(https?://)?((([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})|localhost|(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}))(:\d+)?(/[-a-zA-Z0-9%_.~+]*)*(\?[;&a-zA-Z0-9%_.~+=-]*)?(#[-a-zA-Z0-9_]*)?$",
        ),
        SchemaField(
            name="is_active",
            type="boolean",
            required=False,
        ),
        SchemaField(
            name="status",
            type="string",
            required=False,
            allowed_values=["active", "inactive", "paused", "cancelled"],
        ),
        SchemaField(
            name="cancel_reason",
            type="string",
            required=False,
            max_length=255,
        ),
        SchemaField(
            name="signup_date",
            type="date",
            required=False,
            # cannot be in future (handled via cross-field / not_future rule)
            min_date="1900-01-01",
        ),
        SchemaField(
            name="last_activity_date",
            type="date",
            required=False,
            # cannot be in the less than min signup_date (handled via cross-field / date_order rule)
            min_date="1900-01-01",
        ),
    ],
    cross_field_rules=[
        # date_of_birth cannot be in the future
        CrossFieldRule(
            name="dob_not_future",
            rule_type="not_future",
            field_a="date_of_birth",
        ),
        # signup_date cannot be in the future
        CrossFieldRule(
            name="signup_not_future",
            rule_type="not_future",
            field_a="signup_date",
        ),
        # If status == "cancelled" then cancel_reason must be non-empty
        CrossFieldRule(
            name="cancelled_requires_reason",
            rule_type="conditional_required",
            field_a="status",
            field_b="cancel_reason",
            params={"values": ["cancelled"]},
        ),
        # signup_date should be <= last_activity_date
        CrossFieldRule(
            name="signup_before_last_activity",
            rule_type="date_order",
            field_a="signup_date",
            field_b="last_activity_date",
        ),
    ],
)

def get_current_schema() -> PredefinedSchema:
    return PREDEFINED_SCHEMA
