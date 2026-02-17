from sqlalchemy import Column, String, Text, Integer, Boolean, Date, ForeignKey
from app.db.database import Base

class Mapping(Base):
    __tablename__ = "mappings"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    schema_name = Column(String(255), nullable=False)
    schema_version = Column(String(50), nullable=False)
    mapping_json = Column(Text, nullable=False)

class CustomerImportData(Base):
    __tablename__ = "customer_import_data"

    # Primary key for the record itself
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # timestamp for the load datetime for each upload session
    load_datetime = Column(String, nullable=False)               # Date when the data was loaded

    # Fields from PredefinedSchema "Customer"
    customer_id = Column(String(64), nullable=False, index=True) # Required, max 64
    first_name = Column(String(100), nullable=False)           # Required, max 100
    last_name = Column(String(100), nullable=False)            # Required, max 100
    email = Column(String(255), nullable=False, index=True)    # Required, max 255
    
    date_of_birth = Column(Date, nullable=True)                # Date type
    website = Column(String, nullable=True)                    # Text/String
    is_active = Column(Boolean, nullable=True)                 # Boolean type
    status = Column(String, nullable=True)                     # Enum stored as String
    cancel_reason = Column(String(255), nullable=True)         # Max 255
    signup_date = Column(Date, nullable=True)                  # Date type
    last_activity_date = Column(Date, nullable=True)           # Date type
