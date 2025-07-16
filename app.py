import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import json

from config import config

# Initialize extensions
login_manager = LoginManager()

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Configuration
    config_name = config_name or os.environ.get('FLASK_CONFIG', 'default')
    app.config.from_object(config[config_name])
    
    # Import db from models to avoid circular imports
    from models import db
    
    # Initialize extensions with app
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    
    # Create upload directories
    upload_dirs = [
        'static/uploads',
        'static/uploads/listings',
        'static/uploads/appraisals'
    ]
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)
    
    # Custom Jinja filters
    @app.template_filter('tojsonlist')
    def to_json_list(value):
        if not value:
            return []
        try:
            return json.loads(value)
        except:
            return []
    
    @app.template_filter('from_json')
    def from_json(value):
        if not value:
            return {}
        try:
            return json.loads(value)
        except:
            return {}
    
    # Import models (after db initialization)
    from models import User, Listing, Message, Contact, CustomRequest, AppraisalRequest
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Import and register blueprints
    from routes.main import main_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create tables
    with app.app_context():
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
        if not admin_user:
            admin_user = User(
                username=app.config['ADMIN_USERNAME'],
                password_hash=generate_password_hash(app.config['ADMIN_PASSWORD']),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 