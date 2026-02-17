from typing import List
import re
import difflib

from app.models.mapping import MappingSuggestion, CsvColumn
from app.models.schema_def import PredefinedSchema,SchemaField

# Regex Patterns for common data types
PATTERNS = {
    "email": re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$"),
    "date": re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{1,2}/\d{1,2}/\d{2,4}$"), # YYYY-MM-DD or MM/DD/YYYY
    "integer": re.compile(r"^\d+$"),
    "currency": re.compile(r"^\$?\d{1,3}(,\d{3})*(\.\d+)?$"), # Matches $1,000.00 or 1000.00
    "phone": re.compile(r"^(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}$"),
    "boolean": re.compile(r"^(true|false|yes|no|1|0)$", re.IGNORECASE),
    "uuid": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE),     
    "decimal": re.compile(r"^-?\d*(\.\d+)?$"),  # Matches: 10.5, .5, -10.2, 100 (No commas)    
    "zip_code": re.compile(r"^\d{5}(-\d{4})?$"), # Matches: 90210 or 90210-1234
    "url": re.compile(
        r"^(https?://)?"  # Optional http:// or https://
        r"((([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})|"  # Domain (google.com)
        r"localhost|"  # OR localhost
        r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}))"  # OR IP address
        r"(:\d+)?(/[-a-zA-Z0-9%_.~+]*)*"  # Optional Port and Path
        r"(\?[;&a-zA-Z0-9%_.~+=-]*)?"  # Optional Query String
        r"(#[-a-zA-Z0-9_]*)?$"  # Optional Fragment
    )
}

def normalize_name(name: str) -> str:
    """
    Standardizes a string for comparison.
    Example: "  User_Name " -> "user name"
    """
    name = name.lower().strip()
    
    # Remove special characters (keep only letters, numbers, and spaces)
    name = re.sub(r"[^a-z0-9]+", " ", name)
    
    return name.strip()


def suggest_mappings(columns: List[CsvColumn], schema: PredefinedSchema) -> List[MappingSuggestion]:
    """
    Analyzes CSV columns and guesses which Schema field they belong to.
    It looks at both the header name and the data inside (content).
    """
    suggestions = []

    # Loop through each field we NEED to find in the schema
    for field in schema.fields:
        best_col = None
        best_score = 0.0

        # Compare this schema field against every available CSV column
        for col in columns:
            score = 0.0
            
            # METHOD 1: Name Similarity
            name_score = _calculate_name_similarity(col.name, field.name)
            
            # METHOD 2: Content Analysis
            content_score = analyze_content_match(col.sample_values, field.name)

            # SCORING STRATEGY
            # If the header is generic (e.g., "Column 1"), We rely entirely on the data content.
            if col.name.lower().startswith("column "):
                score = content_score
            else:
                # If we have a real header, trust the name match most.
                # However, if the content match is strong, allow it to boost the score.
                score = max(name_score, content_score * 0.9)

            # Keep track of the best score and column for this specific schema field
            if score > best_score:
                best_score = score
                best_col = col.name

        # Only suggest a mapping if it is reasonably confident (score > 40%)
        if best_col and best_score > 0.4:
            suggestions.append(MappingSuggestion(
                schema_field=field.name,
                csv_column=best_col,
                confidence=best_score
            ))

    return suggestions


def analyze_content_match(samples: List[str], field_name: str) -> float:
    """
    Returns a confidence score (0.0 to 1.0) based on regex matching.
    """
    if not samples:
        return 0.0

    # Map schema field names to regex patterns
    field_lower = field_name.lower()
    
    target_pattern = None

    if "email" in field_lower or "e-mail" in field_lower:
        target_pattern = PATTERNS["email"]

    elif "uuid" in field_lower or "guid" in field_lower:
        target_pattern = PATTERNS["uuid"]

    elif any(x in field_lower for x in ["date", "time", "dob", "birth", "deadline", "period"]):
        target_pattern = PATTERNS["date"]

    elif any(x in field_lower for x in ["price", "cost", "amount", "total", "balance", "revenue", "tax", "fee", "salary", "budget"]):
        target_pattern = PATTERNS["currency"]

    elif "percent" in field_lower or "rate" in field_lower or "ratio" in field_lower or "margin" in field_lower:
        target_pattern = PATTERNS["decimal"] 

    elif "phone" in field_lower or "mobile" in field_lower or "fax" in field_lower:
        target_pattern = PATTERNS["phone"]
        
    elif "zip" in field_lower or "postal" in field_lower:
        target_pattern = PATTERNS["zip_code"]
    
    elif "url" in field_lower or "website" in field_lower or "link" in field_lower or "image" in field_lower:
        target_pattern = PATTERNS["url"]

    elif field_lower.startswith("is_") or field_lower.startswith("has_") or "flag" in field_lower or "enabled" in field_lower:
        target_pattern = PATTERNS["boolean"]

    elif any(x in field_lower for x in ["qty", "quantity", "count", "num", "age", "year"]):
        target_pattern = PATTERNS["integer"]

    # This logic prevents matching for example, "valid" or "width" or "video" as an ID.
    elif field_lower == "id" or field_lower.endswith("_id") or field_lower.endswith("id"):
        target_pattern = PATTERNS["integer"] 
    
    if not target_pattern:
        return 0.0

    # Check how many samples match the pattern
    matches = 0
    for s in samples:
        if target_pattern.match(s):
            matches += 1
            
    return matches / len(samples)

def _calculate_name_similarity(col_name: str, field_name: str) -> float:
    
    # Clean up both names (remove special chars, lowercase, trim)
    c = normalize_name(col_name)
    f = normalize_name(field_name)

    # 1. Perfect Match
    if c == f: 
        return 1.0

    # 2. Schema Field contained in CSV Column (High Confidence)
    # Example: Schema field "email" is inside CSV column "user_email_address"
    if f in c: 
        return 0.8

    # 3. CSV column contained in Schema field (Medium Confidence)
    # Example: CSV Column "date" is inside Schema Field "start_date"
    if c in f: 
        return 0.6

    # No match found
    return 0.0
