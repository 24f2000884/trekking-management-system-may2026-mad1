#app.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tma-mad1-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
