from typing import Dict, List, Optional, Any, Union
import pandas as pd
import re
from datetime import datetime, date

from app.models.mapping import MappingValidationResult
from app.models.schema_def import PredefinedSchema, SchemaField, CrossFieldRule

# Parsing helpers for dates, datetimes, booleans
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
]
DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
]

def parse_date(value: Any) -> Optional[date]:
    """
    Public helper to parse dates from various string formats.
    Returns None if parsing fails or value is empty.
    """
    if pd.isna(value) or value == "" or value is None:
        return None
        
    value_str = str(value).strip()
    
    # Check if already a date object
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value_str, fmt).date()
        except ValueError:
            continue
    return None

def parse_datetime(value: Any) -> Optional[datetime]:
    """
    Public helper to parse datetimes. Falls back to date-only if needed.
    """
    if pd.isna(value) or value == "" or value is None:
        return None
        
    value_str = str(value).strip()

    if isinstance(value, datetime):
        return value

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value_str, fmt)
        except ValueError:
            continue
            
    # Try parsing as date and converting to datetime
    d = parse_date(value_str)
    if d:
        return datetime(d.year, d.month, d.day)
    return None

def parse_bool(value: Any) -> Optional[bool]:
    """
    Public helper to parse boolean values.
    """
    if pd.isna(value) or value == "" or value is None:
        return None
    
    s = str(value).lower().strip()
    if s in ("true", "1", "t", "yes", "y", "on"):
        return True
    if s in ("false", "0", "f", "no", "n", "off"):
        return False
    return None

# VALIDATION LOGIC
#----------------------------------------------------------------
def validate_mapping_structure(
    mapping: Dict[str, str],
    schema: PredefinedSchema,
    available_columns: List[str]
) -> MappingValidationResult:
    """
    Checks if the high-level mapping configuration is valid.
    This runs BEFORE we look at the data inside the file.
    """
    errors: List[str] = []

    # 1. Missing Requirements
    # Check if the user forgot to map any fields marked as 'required' in the schema
    required = schema.required_field_names()
    for field_name in required:
        if field_name not in mapping or not mapping[field_name]:
            errors.append(f"Required field '{field_name}' is not mapped.")

    # 2. Check mapping to missing Columns
    # Check if the user is trying to map a schema field to a column that doesn't exist
    for field_name, col_name in mapping.items():
        if col_name not in available_columns:
            errors.append(
                f"Schema field '{field_name}' is mapped to missing CSV column '{col_name}'."
            )

    return MappingValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
    )

def _validate_field_values(
    field: SchemaField,
    csv_col: str,
    series: pd.Series,
    errors: List[str],
):
    """
    Checks the actual data content of a single column against its schema definition.
    """
    # Filter out empty values and only validate real data
    non_null = series.dropna()
    if non_null.empty:
        return

    # CASE 1: Numeric Fields (Integer/Float)
    if field.type in ("integer", "float"):
        try:
            # Force conversion to numbers; fail if it contains text like "abc"
            converted = pd.to_numeric(non_null, errors='raise')
        except Exception:
            errors.append(
                f"Column '{csv_col}' mapped to '{field.name}' cannot be parsed as {field.type}."
            )
            return

        # Check range constraints (Min/Max values)
        if field.min_value is not None:
            if (converted < field.min_value).any():
                errors.append(
                    f"Column '{csv_col}' mapped to '{field.name}' has values below {field.min_value}."
                )
        if field.max_value is not None:
            if (converted > field.max_value).any():
                errors.append(
                    f"Column '{csv_col}' mapped to '{field.name}' has values above {field.max_value}."
                )

    # CASE 2: Date/Datetime Fields
    elif field.type in ("date", "datetime"):
        parsed_values = []
        for v in non_null:
            # Attempt to parse strictly as Date or Datetime
            if field.type == "date":
                d = parse_date(v)
                if not d:
                    errors.append(
                        f"Column '{csv_col}' mapped to '{field.name}' has invalid date value '{v}'."
                    )
                    continue
                parsed_values.append(d)
            else:
                dt = parse_datetime(v)
                if not dt:
                    errors.append(
                        f"Column '{csv_col}' mapped to '{field.name}' has invalid datetime value '{v}'."
                    )
                    continue
                parsed_values.append(dt)

        # Check Date Range constraints
        if parsed_values:
            if field.min_date:
                min_d = parse_date(field.min_date)
                if min_d and any(v < min_d for v in parsed_values):
                    errors.append(
                        f"Column '{csv_col}' mapped to '{field.name}' "
                        f"has values before minimum allowed date {field.min_date}."
                    )
            if field.max_date:
                max_d = parse_date(field.max_date)
                if max_d and any(v > max_d for v in parsed_values):
                    errors.append(
                        f"Column '{csv_col}' mapped to '{field.name}' "
                        f"has values after maximum allowed date {field.max_date}."
                    )

    # CASE 3: Boolean Fields
    elif field.type == "boolean":
         # Quick check: sample the first 10 rows to see if they look like "true", "yes", "1", etc.
         for v in non_null.head(10):
             if parse_bool(v) is None:
                 errors.append(f"Column '{csv_col}' mapped to '{field.name}' contains non-boolean value '{v}'.")
                 break

    # CASE 4: Allowed Values (Enums)
    # Ensure every value is in the allowed list (e.g. Status must be "Active" or "Inactive")
    if field.allowed_values:
        invalid_values = set(
            v for v in non_null.astype(str) if v not in field.allowed_values
        )
        if invalid_values:
            some = list(invalid_values)[:5]
            errors.append(
                f"Column '{csv_col}' mapped to '{field.name}' contains "
                f"values not in allowed set: {some}..."
            )

    # CASE 5: Strings (Pattern & Length)
    if field.type == "string":
        s = non_null.astype(str)
        
        # Regex Validation
        if field.pattern:
            pattern = re.compile(field.pattern)
            bad = s[~s.str.match(pattern)]
            if not bad.empty:
                sample = bad.head(5).tolist()
                errors.append(
                    f"Column '{csv_col}' mapped to '{field.name}' has values "
                    f"that do not match required pattern (e.g. {sample})."
                )
        
        # Length Validation
        if field.min_length is not None:
            too_short = s[s.str.len() < field.min_length]
            if not too_short.empty:
                errors.append(
                    f"Column '{csv_col}' mapped to '{field.name}' has values shorter than "
                    f"{field.min_length} characters."
                )
        if field.max_length is not None:
            too_long = s[s.str.len() > field.max_length]
            if not too_long.empty:
                errors.append(
                    f"Column '{csv_col}' mapped to '{field.name}' has values longer than "
                    f"{field.max_length} characters."
                )

def _apply_cross_field_rules(
    df: pd.DataFrame,
    mapping: Dict[str, str],
    schema: PredefinedSchema,
    errors: List[str],
):
    """
    Validates rules that involve comparing two columns (e.g., Start Date < End Date).
    """
    today = date.today()

    for rule in schema.cross_field_rules:
        # Rule 1: Not Future Check
        # Ensures a date/datetime field is not set in the future.
        if rule.rule_type == "not_future":
            field = schema.field_by_name(rule.field_a)
            # Skip if field definition or mapping is missing
            if not field or field.type not in ("date", "datetime"):
                continue
            if field.name not in mapping:
                continue
            col = mapping[field.name]
            if col not in df.columns:
                continue

            series = df[col].dropna()
            for v in series:
                parsed = parse_date(v) if field.type == "date" else parse_datetime(v)
                if not parsed:
                    continue
                # Normalize datetimes to date objects for comparison
                d = parsed if isinstance(parsed, date) and not isinstance(parsed, datetime) else parsed.date()
                if d > today:
                    errors.append(
                        f"Field '{field.name}' (column '{col}') has value '{v}' "
                        f"in the future (rule: {rule.name})."
                    )
                    break

        # Rule 2: Date Order Check
        # Ensures Field A happens on or before Field B (e.g. signup_date <= last_activity_date)
        elif rule.rule_type == "date_order":
            f_a = schema.field_by_name(rule.field_a)
            f_b = schema.field_by_name(rule.field_b) if rule.field_b else None
            
            # Skip if fields or mappings are missing
            if not f_a or not f_b:
                continue
            if f_a.name not in mapping or f_b.name not in mapping:
                continue

            col_a = mapping[f_a.name]
            col_b = mapping[f_b.name]
            if col_a not in df.columns or col_b not in df.columns:
                continue

            # Load the data columns
            s_a = df[col_a]
            s_b = df[col_b]

            # Only validate rows where BOTH dates exist
            mask = s_a.notna() & s_b.notna()
            
            # Extract valid pairs to loop through
            vals_a = s_a[mask]
            vals_b = s_b[mask]

            for v_a, v_b in zip(vals_a, vals_b):
                d_a = parse_date(v_a) or (parse_datetime(v_a) or None)
                d_b = parse_date(v_b) or (parse_datetime(v_b) or None)
                
                if not d_a or not d_b:
                    continue
                
                # Normalize both to dates for comparison
                val_a = d_a.date() if isinstance(d_a, datetime) else d_a
                val_b = d_b.date() if isinstance(d_b, datetime) else d_b

                if val_a > val_b:
                    errors.append(
                        f"Rule '{rule.name}' violated: '{f_a.name}' ({v_a}) "
                        f"should be on or before '{f_b.name}' ({v_b})."
                    )
                    break

        # Rule 3: Conditional Requirement
        # If status == "cancelled" then cancel_reason must be non-empty
        elif rule.rule_type == "conditional_required":
            f_a = schema.field_by_name(rule.field_a)
            f_b = schema.field_by_name(rule.field_b) if rule.field_b else None
            if not f_a or not f_b:
                continue
            if f_a.name not in mapping or f_b.name not in mapping:
                continue

            col_a = mapping[f_a.name]
            col_b = mapping[f_b.name]
            if col_a not in df.columns or col_b not in df.columns:
                continue

            # The values in Column A that trigger the requirement (e.g., ["cancelled",...])
            trigger_values = set(rule.params.get("values", []))
            
            s_a = df[col_a].astype(str)
            s_b = df[col_b]

            # Find rows where Column A matches the trigger
            mask = s_a.isin(trigger_values)
            
            # Find rows where the trigger fired BUT Column B is empty
            violating_rows = s_b[mask & s_b.isna()]
            
            if not violating_rows.empty:
                errors.append(
                    f"Rule '{rule.name}' violated: when '{f_a.name}' is one of "
                    f"{list(trigger_values)}, '{f_b.name}' must be non-empty."
                )

def validate_csv_rows(
    file_path: str,
    has_header: bool,
    delimiter: str,
    mapping: Dict[str, str],
    schema: PredefinedSchema,
    max_rows: int = 1000, # limited default sample size for validation
) -> MappingValidationResult:
    """
    Main entry point for data validation.
    Reads a sample of the CSV and runs all field and cross-field checks.
    """
    errors: List[str] = []

    try:
        # Load sample data
        # Reading everything as 'string' (dtype=str) to prevent Pandas from guessing types wrong
        df = pd.read_csv(
            file_path,
            sep=delimiter,
            header=0 if has_header else None,
            nrows=max_rows,
            dtype=str, 
            skip_blank_lines=True
        )
    except Exception as e:
        return MappingValidationResult(is_valid=False, errors=[f"Failed to read CSV for validation: {str(e)}"])

    # If no header exists, generate "Column_1", "Column_2", ...
    if not has_header:
        df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]

    # Phase 1: Validate individual columns (Types, Ranges, Regex)
    for field in schema.fields:
        if field.name not in mapping:
            continue
        csv_col = mapping[field.name]
        
        # Skip if the mapped column is somehow missing from the dataframe
        if csv_col not in df.columns:
            continue

        series = df[csv_col]

        # Check 'Required' constraints (cannot be empty)
        if field.required:
            if series.isna().all() or (series == "").all():
                errors.append(
                    f"Required field '{field.name}' mapped to column '{csv_col}' "
                    f"contains only empty values in the sample."
                )

        _validate_field_values(field, csv_col, series, errors)

    # Phase 2: Validate relationships between columns (Dates, Conditionals)
    _apply_cross_field_rules(df, mapping, schema, errors)

    return MappingValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
    )
