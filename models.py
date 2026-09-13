from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    items = db.Column(db.String, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    order_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Boolean, default=True)