import csv
import os
import uuid
from typing import Dict, List, Tuple
import pandas as pd

from app.core.config import settings
from app.models.mapping import CsvColumn

def save_uploaded_file(upload_file) -> str:
    """
    Streams uploaded file to disk to safely handle up to 100 MB.
    Returns a generated file_id (UUID-like) used to reference it later.
    """
    file_id = str(uuid.uuid4())
    dest_path = os.path.join(settings.UPLOAD_DIR, file_id + ".csv")

    size = 0
    with open(dest_path, "wb") as out_file:
        for chunk in iter(lambda: upload_file.file.read(1024 * 1024), b""):
            size += len(chunk)
            if size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                out_file.close()
                os.remove(dest_path)
                raise ValueError("File too large. Max size is 100 MB.")
            out_file.write(chunk)

    return file_id

def get_file_path(file_id: str) -> str:
    path = os.path.join(settings.UPLOAD_DIR, file_id + ".csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No file found for id {file_id}")
    return path

def detect_header(file_path: str, encoding: str = "utf-8", sample_bytes: int = 2048) -> bool:
    """
    Attempts to guess if a CSV file has a header row using csv.Sniffer.
    """
    if not os.path.exists(file_path):
        return True  

    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            sample = f.read(sample_bytes)
            # Sniffer raises an error if the sample is too small or malformed
            has_header = csv.Sniffer().has_header(sample)
            return has_header
    except csv.Error:
        # If Sniffer fails (e.g. weird delimiters), fallback to True
        return True
    except Exception:
        return True
 
def inspect_columns(
    file_id: str, 
    has_header: bool, 
    delimiter: str = ",", 
    encoding: str = "utf-8"
) -> List[CsvColumn]:

    file_path = get_file_path(file_id)
    
    if not os.path.exists(file_path):
        raise ValueError("File not found")

    columns: List[CsvColumn] = []

    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            reader = csv.reader(f, delimiter=delimiter)
            
            try:
                first_row = next(reader)
            except StopIteration:
                return [] # Empty file

            # Determine Column Names
            if has_header:
                headers = first_row
                # If we have a header, we need to read the NEXT rows for samples
                data_rows = []
                for _ in range(5):
                    try:
                        data_rows.append(next(reader))
                    except StopIteration:
                        break
            else:
                # If no header, the first row IS data
                headers = [f"Column {i+1}" for i in range(len(first_row))]
                data_rows = [first_row]
                for _ in range(4): # Get 4 more to have 5 samples
                    try:
                        data_rows.append(next(reader))
                    except StopIteration:
                        break
       
            num_cols = len(headers)
            
            for i in range(num_cols):
                samples = []
                for row in data_rows:
                    if len(row) > i:
                        val = row[i].strip()
                        if val: # Only add non-empty values
                            samples.append(val)
                
                columns.append(CsvColumn(
                    name=headers[i], 
                    index=i, 
                    sample_values=samples
                ))

    except Exception as e:
        print(f"Error inspecting columns: {e}")
        return []

    return columns

def get_rows(
    file_id: str, 
    has_header: bool, 
    delimiter: str = ",", 
    encoding: str = "utf-8"
) -> List[Dict[str, str]]:
    """
    Reads a CSV file and converts it into a list of dictionaries.
    Example output: [{'Name': 'Alice', 'Age': '30'}, {'Name': 'Bob', 'Age': '25'}]
    """
    file_path = get_file_path(file_id)
    
    if not os.path.exists(file_path):
        raise ValueError("File not found")

    rows_out: List[Dict[str, str]] = []

    try:
        # Open file with 'replace' to prevent crashing on bad characters
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            
            # CASE 1: File has a header row
            if has_header:
                # DictReader automatically uses the first row as keys
                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    # Clean up data by stripping whitespace from keys and values
                    clean_row = {k.strip() if k else k: v.strip() if v else v for k, v in row.items()}
                    rows_out.append(clean_row)
            
            # CASE 2: File has no header row
            else:
                reader = csv.reader(f, delimiter=delimiter)
                
                # Load all data first so we can handle rows with different column counts
                all_rows = list(reader)
                if not all_rows:
                    return []
                
                # Find the widest row to ensure we generate enough generic headers
                max_cols = max(len(r) for r in all_rows)
                
                # Create generic headers: "Column 1", "Column 2", etc.
                headers = [f"Column {i+1}" for i in range(max_cols)]
                
                for r in all_rows:
                    # If this row is shorter than the widest row, add empty strings to match length
                    padded = r + [""] * (max_cols - len(r))
                    
                    # Map the generic headers to the row values
                    row_dict = {h: val.strip() for h, val in zip(headers, padded)}
                    rows_out.append(row_dict)

    except Exception as e:
        print(f"Error reading rows: {e}")
        raise e

    return rows_out
