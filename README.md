# E-Commerce Furniture Website - Backend

Backend API for an AI-powered furniture e-commerce platform built with FastAPI and MySQL.

## Features

- REST APIs
- JWT Authentication
- Role-Based Authorization
- Product Management
- User Management
- AI Room Decoration API
- Image Upload
- Database Migrations

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- Alembic
- MySQL
- Pydantic
- Google AI Studio (Gemini)
- Pillow

## Installation

Go to the project directory


## Create a virtual environment

python -m venv venv


Activate the virtual environment

### Windows

venv\Scripts\activate


### Linux / macOS

source venv/bin/activate


## Install dependencies

pip install -r requirements.txt


Run database migrations

alembic upgrade head

Start the server

uvicorn app.main:app --reload


The API will run at:

http://localhost:8000
