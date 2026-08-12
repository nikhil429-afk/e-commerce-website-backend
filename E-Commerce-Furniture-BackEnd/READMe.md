# E-Commerce Furniture Website - Backend

Backend of an AI- Powered  E-Commerce platform built with Python (FastAPI)


## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- Alembic
- MySQL
- Pydantic
- Google AI Studio (Gemini)
- Pillow


## Project Structure

.venv/

.alembic/

    versions/
        conains all the changes in the database made through the alembic migrations.
    .env.py

app/
    assets/
        contains all the images of products uploaded

    core/
        contains database connection, authorization logic
    
    models/
        contains all the pydantic validations of the database tables

    routes/
        contains all the routes of the pages used in the project

    schema/
        contains all the schema for the database tables
    
    services/
        contains the ai room decoration logic

    main.py

.env
.gitignore
alembic.ini
requirements.txt


## Installation

python -m venv venv  <-- Create a Virtual environment 

Activate the virtual environment

### Windows

venv\Scripts\activate


### Linux / macOS

source venv/bin/activate


## Install dependencies

pip install -r requirements.txt


Create a `.env` file

DATABASE_URL=your_database_url
SECRET_KEY=your_secret_key
GOOGLE_API_KEY=your_google_api_key


Run database migrations

alembic upgrade head

Start the server

uvicorn app.main:app --reload


The API will run at:

http://localhost:8000