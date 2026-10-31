from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_owner
from app.schema.contact import Contact
from app.models.contact import ContactCreate, ContactResponse

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("/", response_model=ContactResponse)
def create_contact(data: ContactCreate,user=Depends(get_current_user), db: Session = Depends(get_db)):

    new_contact = Contact(user_id=user.id, name=data.name, email=data.email, phone=data.phone, subject=data.subject, message=data.message, appointment_date=data.appointment_date)

    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)

    return new_contact


@router.get("/", response_model=list[ContactResponse])
def get_contacts(db: Session = Depends(get_db), owner=Depends(require_owner)):
    return db.query(Contact).all()


@router.get("/appointments", response_model=list[ContactResponse])
def get_appointments(db: Session = Depends(get_db), owner=Depends(require_owner)):
    return db.query(Contact).filter(Contact.subject == "Showroom Visit").all()


