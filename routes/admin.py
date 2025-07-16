from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from models import db, User, Listing, Contact, Message, CustomRequest, AppraisalRequest
import json
import os
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    """Admin logout"""
    logout_user()
    return redirect(url_for('main.index'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard"""
    # Get summary statistics
    total_listings = Listing.query.count()
    active_listings = Listing.query.filter_by(is_active=True).count()
    total_messages = Message.query.count()
    unread_messages = Message.query.filter_by(is_read=False, sender_type='customer').count()
    pending_custom_requests = CustomRequest.query.filter_by(status='pending').count()
    pending_appraisals = AppraisalRequest.query.filter_by(status='pending').count()
    
    # Recent activity
    recent_messages = Message.query.filter_by(sender_type='customer').order_by(Message.created_at.desc()).limit(5).all()
    recent_custom_requests = CustomRequest.query.order_by(CustomRequest.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_listings=total_listings,
                         active_listings=active_listings,
                         total_messages=total_messages,
                         unread_messages=unread_messages,
                         pending_custom_requests=pending_custom_requests,
                         pending_appraisals=pending_appraisals,
                         recent_messages=recent_messages,
                         recent_custom_requests=recent_custom_requests)

@admin_bp.route('/listings')
@login_required
def listings():
    """Manage listings"""
    page = request.args.get('page', 1, type=int)
    listings = Listing.query.order_by(Listing.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/listings.html', listings=listings)

@admin_bp.route('/listings/new', methods=['GET', 'POST'])
@login_required
def new_listing():
    """Create new listing"""
    if request.method == 'POST':
        listing = Listing(
            title=request.form.get('title'),
            sku=request.form.get('sku'),
            category=request.form.get('category'),
            retail_value=float(request.form.get('retail_value', 0)),
            sale_price=float(request.form.get('sale_price', 0)),
            description=request.form.get('description'),
            
            # Center stone details
            center_stone=request.form.get('center_stone'),
            center_shape=request.form.get('center_shape'),
            center_carat_weight=float(request.form.get('center_carat_weight', 0)) if request.form.get('center_carat_weight') else None,
            center_color=request.form.get('center_color'),
            center_clarity=request.form.get('center_clarity'),
            center_certification=request.form.get('center_certification'),
            
            # Secondary stone details
            secondary_shape=request.form.get('secondary_shape'),
            secondary_carat_weight=float(request.form.get('secondary_carat_weight', 0)) if request.form.get('secondary_carat_weight') else None,
            secondary_color=request.form.get('secondary_color'),
            secondary_clarity=request.form.get('secondary_clarity'),
            
            # Setting details
            total_carat_weight=float(request.form.get('total_carat_weight', 0)) if request.form.get('total_carat_weight') else None,
            metal=request.form.get('metal'),
            ring_size=request.form.get('ring_size'),
            setting_retail_value=float(request.form.get('setting_retail_value', 0)) if request.form.get('setting_retail_value') else None
        )
        
        # Handle customization options
        options = {}
        option_keys = ['metal_options', 'size_options', 'stone_options']
        for key in option_keys:
            if request.form.get(key):
                options[key] = request.form.get(key).split(',')
        
        if options:
            listing.options = json.dumps(options)
        
        # Handle image uploads
        images = []
        for i in range(5):  # Allow up to 5 images
            if f'image_{i}' in request.files:
                file = request.files[f'image_{i}']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join('static/uploads/listings', filename)
                    os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                    file.save(upload_path)
                    images.append(upload_path)
        
        if images:
            listing.images = json.dumps(images)
        
        db.session.add(listing)
        db.session.commit()
        
        flash('Listing created successfully!')
        return redirect(url_for('admin.listings'))
    
    return render_template('admin/listing_form.html', listing=None)

@admin_bp.route('/listings/<int:listing_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_listing(listing_id):
    """Edit existing listing"""
    listing = Listing.query.get_or_404(listing_id)
    
    if request.method == 'POST':
        listing.title = request.form.get('title')
        listing.sku = request.form.get('sku')
        listing.category = request.form.get('category')
        listing.retail_value = float(request.form.get('retail_value', 0))
        listing.sale_price = float(request.form.get('sale_price', 0))
        listing.description = request.form.get('description')
        
        # Update stone details
        listing.center_stone = request.form.get('center_stone')
        listing.center_shape = request.form.get('center_shape')
        listing.center_carat_weight = float(request.form.get('center_carat_weight', 0)) if request.form.get('center_carat_weight') else None
        listing.center_color = request.form.get('center_color')
        listing.center_clarity = request.form.get('center_clarity')
        listing.center_certification = request.form.get('center_certification')
        
        listing.secondary_shape = request.form.get('secondary_shape')
        listing.secondary_carat_weight = float(request.form.get('secondary_carat_weight', 0)) if request.form.get('secondary_carat_weight') else None
        listing.secondary_color = request.form.get('secondary_color')
        listing.secondary_clarity = request.form.get('secondary_clarity')
        
        listing.total_carat_weight = float(request.form.get('total_carat_weight', 0)) if request.form.get('total_carat_weight') else None
        listing.metal = request.form.get('metal')
        listing.ring_size = request.form.get('ring_size')
        listing.setting_retail_value = float(request.form.get('setting_retail_value', 0)) if request.form.get('setting_retail_value') else None
        
        listing.is_active = 'is_active' in request.form
        listing.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Listing updated successfully!')
        return redirect(url_for('admin.listings'))
    
    return render_template('admin/listing_form.html', listing=listing)

@admin_bp.route('/messages')
@login_required
def messages():
    """View and manage messages"""
    page = request.args.get('page', 1, type=int)
    
    # Get all contacts with their latest message
    subquery = db.session.query(
        Message.contact_id,
        db.func.max(Message.created_at).label('latest_message')
    ).group_by(Message.contact_id).subquery()
    
    contacts_with_messages = db.session.query(Contact, subquery.c.latest_message)\
        .join(subquery, Contact.id == subquery.c.contact_id)\
        .order_by(subquery.c.latest_message.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/messages.html', contacts=contacts_with_messages)

@admin_bp.route('/messages/<int:contact_id>')
@login_required
def view_messages(contact_id):
    """View messages for a specific contact"""
    contact = Contact.query.get_or_404(contact_id)
    messages = Message.query.filter_by(contact_id=contact_id).order_by(Message.created_at.asc()).all()
    
    # Mark customer messages as read
    Message.query.filter_by(contact_id=contact_id, sender_type='customer', is_read=False).update({'is_read': True})
    db.session.commit()
    
    return render_template('admin/conversation.html', contact=contact, messages=messages)

@admin_bp.route('/send_admin_message', methods=['POST'])
@login_required
def send_admin_message():
    """Send message as admin"""
    contact_id = request.form.get('contact_id')
    content = request.form.get('content')
    
    if not contact_id or not content:
        return jsonify({'error': 'Missing required fields'}), 400
    
    message = Message(
        contact_id=contact_id,
        sender_type='admin',
        content=content
    )
    
    # Handle file upload
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_path = os.path.join('static/uploads', filename)
            file.save(upload_path)
            message.attachment_url = upload_path
            
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                message.attachment_type = 'image'
            elif filename.lower().endswith(('.mp4', '.mov', '.avi')):
                message.attachment_type = 'video'
            else:
                message.attachment_type = 'file'
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/custom_requests')
@login_required
def custom_requests():
    """View and manage custom requests"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', None)
    
    query = CustomRequest.query
    if status:
        query = query.filter_by(status=status)
    
    requests = query.order_by(CustomRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/custom_requests.html', requests=requests, current_status=status)

@admin_bp.route('/custom_requests/<int:request_id>')
@login_required
def view_custom_request(request_id):
    """View detailed custom request"""
    custom_request = CustomRequest.query.get_or_404(request_id)
    return render_template('admin/custom_request_detail.html', request=custom_request)

@admin_bp.route('/update_custom_request/<int:request_id>', methods=['POST'])
@login_required
def update_custom_request(request_id):
    """Update custom request status and notes"""
    custom_request = CustomRequest.query.get_or_404(request_id)
    
    custom_request.status = request.form.get('status')
    custom_request.admin_notes = request.form.get('admin_notes')
    custom_request.updated_at = datetime.utcnow()
    
    db.session.commit()
    flash('Custom request updated successfully!')
    
    return redirect(url_for('admin.view_custom_request', request_id=request_id))

@admin_bp.route('/appraisal_requests')
@login_required
def appraisal_requests():
    """View and manage appraisal requests"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', None)
    
    query = AppraisalRequest.query
    if status:
        query = query.filter_by(status=status)
    
    requests = query.order_by(AppraisalRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/appraisal_requests.html', requests=requests, current_status=status)

@admin_bp.route('/appraisal_requests/<int:request_id>')
@login_required
def view_appraisal_request(request_id):
    """View detailed appraisal request"""
    appraisal_request = AppraisalRequest.query.get_or_404(request_id)
    return render_template('admin/appraisal_request_detail.html', request=appraisal_request)

@admin_bp.route('/update_appraisal_request/<int:request_id>', methods=['POST'])
@login_required
def update_appraisal_request(request_id):
    """Update appraisal request status and notes"""
    appraisal_request = AppraisalRequest.query.get_or_404(request_id)
    
    appraisal_request.status = request.form.get('status')
    appraisal_request.payment_status = request.form.get('payment_status')
    appraisal_request.admin_notes = request.form.get('admin_notes')
    appraisal_request.updated_at = datetime.utcnow()
    
    # Handle appraisal document upload
    if 'appraisal_document' in request.files:
        file = request.files['appraisal_document']
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_path = os.path.join('static/uploads/appraisals', filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            appraisal_request.appraisal_document = upload_path
    
    db.session.commit()
    flash('Appraisal request updated successfully!')
    
    return redirect(url_for('admin.view_appraisal_request', request_id=request_id)) 