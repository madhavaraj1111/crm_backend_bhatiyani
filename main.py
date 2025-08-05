from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./crm.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class ContactDB(Base):
    """
    SQLAlchemy model for Contact table
    Stores contact information with timestamps
    """
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    company = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic Models
class ContactBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class ContactUpdate(ContactBase):
    name: Optional[str] = None
    email: Optional[str] = None

class Contact(ContactBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app initialization
app = FastAPI(
    title="CRM API",
    description="A comprehensive CRM API with full CRUD operations",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
def get_db():
    """
    Database dependency function
    Creates and closes database sessions properly
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Routes - Full CRUD Operations

@app.get("/")
def read_root():
    """Root endpoint with API information"""
    return {
        "message": "CRM API is running",
        "version": "1.0.0",
        "endpoints": ["/contacts", "/contacts/{id}"]
    }

@app.get("/contacts", response_model=List[Contact])
def get_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all contacts with pagination
    AI Used: Pagination logic optimized with ChatGPT
    """
    contacts = db.query(ContactDB).offset(skip).limit(limit).all()
    return contacts

@app.get("/contacts/{contact_id}", response_model=Contact)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific contact by ID
    Raises 404 if contact not found
    """
    contact = db.query(ContactDB).filter(ContactDB.id == contact_id).first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@app.post("/contacts", response_model=Contact)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    """
    Create a new contact
    Validates email uniqueness
    """
    # Check if email already exists
    existing_contact = db.query(ContactDB).filter(ContactDB.email == contact.email).first()
    if existing_contact:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_contact = ContactDB(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@app.put("/contacts/{contact_id}", response_model=Contact)
def update_contact(contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db)):
    """
    Update an existing contact
    Only updates provided fields (partial update)
    """
    db_contact = db.query(ContactDB).filter(ContactDB.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Update only provided fields
    update_data = contact.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_contact, field, value)
    
    db_contact.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_contact)
    return db_contact

@app.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    """
    Delete a contact by ID
    Returns confirmation message
    """
    db_contact = db.query(ContactDB).filter(ContactDB.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    db.delete(db_contact)
    db.commit()
    return {"message": f"Contact {contact_id} deleted successfully"}

@app.get("/contacts/search/{query}")
def search_contacts(query: str, db: Session = Depends(get_db)):
    """
    Search contacts by name, email, or company
    Case-insensitive search across multiple fields
    """
    contacts = db.query(ContactDB).filter(
        (ContactDB.name.ilike(f"%{query}%")) |
        (ContactDB.email.ilike(f"%{query}%")) |
        (ContactDB.company.ilike(f"%{query}%"))
    ).all()
    return contacts

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)