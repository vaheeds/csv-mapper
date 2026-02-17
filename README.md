# CSV Mapper (Skill Challenge Project)

This application allows users to upload CSV files and map its columns to a predefined schema.

I used a **sample customer entity** with the following fields as the predefined schema. More schema details and constraints are defined in the **/app/models** folder.

- customer_id\* (Required)
- first_name\* (Required)
- last_name\* (Required)
- email\* (Required)
- date_of_birth
- website
- is_active
- status
- cancel_reason
- signup_date
- last_activity_date

## Project Structure

```
rootfolder/
│
├── app/                          # Backend application
│   ├── api/
│   │   └── routes.py            # FastAPI routes
│   ├── core/
│   │   └── config.py            # Configuration
│   ├── db/
│   │   ├── database.py          # Database setup
│   │   └── models.py            # Database models
│   ├── models/
│   │   ├── errors.py            # Error models
│   │   ├── mapping.py           # Mapping models
│   │   └── schema_def.py        # Schema definition
│   ├── services/
│   │   ├── csv_loader.py        # CSV file handling
│   │   ├── mapping_store.py     # Mapping persistence
│   │   ├── mapping_suggester.py # Auto-suggestion logic
│   │   └── validator.py         # Validation logic
│   └── main.py                  # Application entry point
│
├── ui/                          # Frontend application (React + Vite)
│   ├── src/                     # React source code
│   ├── package.json             # React dependencies
│   ├── tsconfig.json
│   └── vite.config.ts
├── tests/                        # Backend tests
│   ├── test_api_router.py
│   ├── test_csv_loader.py
│   ├── test_mapping_store.py
│   ├── test_mapping_suggester.py
│   ├── test_schema_def.py
│   └── test_validator.py
├── data/                         # Data files
│   └── dummy/                    # Sample CSV files
├── uploads/                      # Temporary uploaded files
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 22+
- npm

### Backend Setup

1. **Navigate to the project root**

   ```bash
   cd c:\path\to\project-root
   ```

2. **Activate the Python virtual environment**

   If a python virtual environment (e.g. the `env/` folder) doesn't exist, create and activate a new virtual environment:

   ```bash
   # Windows
   python -m venv env
   env\Scripts\activate

   # macOS/Linux
   python3 -m venv env
   source env/bin/activate
   ```

   If the python virtual environment (e.g. `env` ) already exists, simply activate it:

   ```bash
   # Windows
   env\Scripts\activate

   # macOS/Linux
   source env/bin/activate
   ```

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the backend server**

   ```bash
   uvicorn app.main:app --reload
   ```

   The backend API will be available at `http://localhost:8000`

   **Access the interactive API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Frontend Setup

1. **Navigate to the UI folder**

   ```bash
   cd ui
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Run the development server**
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173` (or another port if 5173 is in use)

### Running Tests

Tests are located in the `/tests` folder.

1. **From the project root**, run all tests:

   ```bash
   pytest
   ```

2. **Run specific test file**:

   ```bash
   pytest .\tests\test_mapping_suggester.py
   ```

3. **Run with verbose output**:
   ```bash
   pytest -v
   ```

## API Endpoints

- `GET /schema` - Get the predefined schema
- `POST /upload` - Upload a CSV file
- `GET /columns` - Get columns from an uploaded file
- `GET /suggest-mapping` - Get auto-suggested mappings
- `GET /preview` - Preview file contents
- `POST /validate-mapping` - Validate a mapping
- `POST /mapping` - Save a mapping
- `POST /ingest-data` - Save the CSV data
- `GET /mappings` - List all saved mappings
- `GET /mappings/{mapping_id}` - Get a specific mapping

## Troubleshooting

### Backend Issues

- Ensure the Python virtual environment is activated
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify the server is running on the correct port

### Frontend Issues

- Ensure Node.js and npm are installed
- Try deleting `node_modules` and `package-lock.json`, then run `npm install` again
- Check that the frontend can reach the backend API (CORS may need configuration)

### Test Failures

- Ensure the virtual environment is activated
- Verify all dependencies are installed
- Check file paths in test configurations
