from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# This will be initialized in app.py
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='contact', lazy=True)
    custom_requests = db.relationship('CustomRequest', backref='contact', lazy=True)
    appraisal_requests = db.relationship('AppraisalRequest', backref='contact', lazy=True)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    retail_value = db.Column(db.Float, nullable=False)
    sale_price = db.Column(db.Float, nullable=False)
    
    # Center Stone Details
    center_stone = db.Column(db.String(50))
    center_shape = db.Column(db.String(50))
    center_carat_weight = db.Column(db.Float)
    center_color = db.Column(db.String(10))
    center_clarity = db.Column(db.String(10))
    center_certification = db.Column(db.String(50))
    
    # Secondary Stone Details
    secondary_shape = db.Column(db.String(50))
    secondary_carat_weight = db.Column(db.Float)
    secondary_color = db.Column(db.String(10))
    secondary_clarity = db.Column(db.String(10))
    
    # Setting Details
    total_carat_weight = db.Column(db.Float)
    metal = db.Column(db.String(50))
    options = db.Column(db.Text)  # JSON string for customization options
    ring_size = db.Column(db.String(10))
    setting_retail_value = db.Column(db.Float)
    
    # Additional fields
    description = db.Column(db.Text)
    images = db.Column(db.Text)  # JSON string for image URLs
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'customer' or 'admin'
    content = db.Column(db.Text, nullable=False)
    attachment_url = db.Column(db.String(255))  # For images, videos, files
    attachment_type = db.Column(db.String(20))  # 'image', 'video', 'file'
    listing_customization = db.Column(db.Text)  # JSON string for ring customizations
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class CustomRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    reference_images = db.Column(db.Text)  # JSON string for image URLs
    reference_links = db.Column(db.Text)  # JSON string for links
    budget_range = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, declined
    admin_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AppraisalRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    item_description = db.Column(db.Text, nullable=False)
    item_images = db.Column(db.Text)  # JSON string for image URLs
    existing_certificates = db.Column(db.Text)  # JSON string for certificate images
    appraisal_purpose = db.Column(db.String(100))  # insurance, sale, etc.
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, completed
    appraisal_document = db.Column(db.String(255))  # URL to completed appraisal
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    admin_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 