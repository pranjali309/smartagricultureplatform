# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# -----------------------------
# Users Table
# -----------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username}>"

# -----------------------------
# Weather Records
# -----------------------------
class Weather(db.Model):
    __tablename__ = 'weather'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Weather {self.location}>"

# -----------------------------
# AI Tool Usage
# -----------------------------
class AIToolUsage(db.Model):
    __tablename__ = 'ai_usage'
    id = db.Column(db.Integer, primary_key=True)
    tool_name = db.Column(db.String(50))
    usage_count = db.Column(db.Integer, default=0)
    used_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AITool {self.tool_name}>"

# -----------------------------
# Market Price Records
# -----------------------------
class MarketPrice(db.Model):
    __tablename__ = 'market_prices'
    id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(50))
    price = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.utcnow)

    def __repr__(self):
        return f"<MarketPrice {self.crop_name} - {self.price}>"

# -----------------------------
# Farm Data (e.g., soil moisture)
# -----------------------------
class FarmData(db.Model):
    __tablename__ = 'farm_data'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100))
    soil_moisture = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FarmData {self.location}>"

# -----------------------------
# User Login Activity
# -----------------------------
class LoginActivity(db.Model):
    __tablename__ = 'login_activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    login_time = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='logins')

    def __repr__(self):
        return f"<LoginActivity User {self.user_id} at {self.login_time}>"
