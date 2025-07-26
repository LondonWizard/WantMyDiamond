from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from models import db, User, Listing, Contact, Message, CustomRequest, AppraisalRequest, ListingImage
import json
import os
import base64
import uuid
from datetime import datetime
from PIL import Image
import io

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
        category = request.form.get('category')
        shape = request.form.get('center_shape')
        sku = request.form.get('sku')
        
        listing = Listing(
            title=request.form.get('title'),
            sku=sku,
            category=category,
            retail_value=float(request.form.get('retail_value', 0)),
            sale_price=float(request.form.get('sale_price', 0)),
            description=request.form.get('description'),
            
            # Center stone details
            center_stone=request.form.get('center_stone'),
            center_shape=shape,
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
        
        # Handle image uploads - Store in gallery structure
        images = []
        if category and shape and sku:
            # Create gallery-style directory structure
            gallery_path = os.path.join('static/WMD_Photos_NoVideos', category, shape, sku)
            os.makedirs(gallery_path, exist_ok=True)
            
            for i in range(10):  # Allow up to 10 images
                if f'image_{i}' in request.files:
                    file = request.files[f'image_{i}']
                    if file and file.filename:
                        # Use timestamp + original filename for uniqueness
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        file_ext = os.path.splitext(file.filename)[1].lower()
                        filename = f"{timestamp}_{i}{file_ext}"
                        upload_path = os.path.join(gallery_path, filename)
                        
                        file.save(upload_path)
                        # Store relative path for gallery access
                        relative_path = f"/static/WMD_Photos_NoVideos/{category}/{shape}/{sku}/{filename}"
                        images.append(relative_path)
        
        if images:
            listing.images = json.dumps(images)
        
        db.session.add(listing)
        db.session.commit()
        
        flash('Listing created successfully and added to gallery!')
        return redirect(url_for('admin.listings'))
    
    # Get gallery categories for form
    from routes.gallery import JEWELRY_CATEGORIES, DIAMOND_SHAPES
    return render_template('admin/listing_form.html', 
                         listing=None, 
                         gallery_categories=JEWELRY_CATEGORIES,
                         diamond_shapes=DIAMOND_SHAPES)

@admin_bp.route('/listings/<int:listing_id>/edit-overlay', methods=['GET', 'POST'])
@login_required
def edit_listing_overlay(listing_id):
    """Enhanced listing editor with website overlay view"""
    listing = Listing.query.get_or_404(listing_id)
    
    if request.method == 'POST':
        try:
            # Update basic fields
            listing.title = request.form.get('title')
            listing.sku = request.form.get('sku')
            listing.category = request.form.get('category')
            listing.center_shape = request.form.get('center_shape')
            listing.retail_value = float(request.form.get('retail_value', 0))
            listing.sale_price = float(request.form.get('sale_price', 0))
            listing.description = request.form.get('description')
            listing.is_active = bool(request.form.get('is_active'))
            
            db.session.commit()
            flash('Listing updated successfully!', 'success')
            
            # Return JSON response for AJAX
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': True, 'message': 'Listing updated successfully!'})
            
            return redirect(url_for('admin.edit_listing_overlay', listing_id=listing_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating listing: {str(e)}', 'error')
            
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'error': str(e)}), 400
    
    return render_template('admin/listing_form_overlay.html', listing=listing)

@admin_bp.route('/listings/new-overlay', methods=['GET', 'POST'])
@login_required
def new_listing_overlay():
    """Create new listing with overlay editor"""
    if request.method == 'POST':
        try:
            listing = Listing(
                title=request.form.get('title'),
                sku=request.form.get('sku'),
                category=request.form.get('category'),
                center_shape=request.form.get('center_shape'),
                retail_value=float(request.form.get('retail_value', 0)),
                sale_price=float(request.form.get('sale_price', 0)),
                description=request.form.get('description'),
                is_active=bool(request.form.get('is_active'))
            )
            
            db.session.add(listing)
            db.session.commit()
            
            flash('Listing created successfully!', 'success')
            return redirect(url_for('admin.edit_listing_overlay', listing_id=listing.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating listing: {str(e)}', 'error')
    
    return render_template('admin/listing_form_overlay.html', listing=None)

@admin_bp.route('/listings/<int:listing_id>/edit-split', methods=['GET', 'POST'])
@login_required
def edit_listing_split(listing_id):
    """Split-screen listing editor with live preview"""
    listing = Listing.query.get_or_404(listing_id)
    
    if request.method == 'POST':
        try:
            # Update all fields
            listing.title = request.form.get('title')
            listing.sku = request.form.get('sku')
            listing.category = request.form.get('category')
            listing.center_shape = request.form.get('center_shape')
            listing.retail_value = float(request.form.get('retail_value', 0))
            listing.sale_price = float(request.form.get('sale_price', 0))
            listing.description = request.form.get('description')
            listing.is_active = bool(request.form.get('is_active'))
            
            # Stone details
            listing.center_stone = request.form.get('center_stone')
            listing.center_carat_weight = float(request.form.get('center_carat_weight', 0)) if request.form.get('center_carat_weight') else None
            listing.center_color = request.form.get('center_color')
            listing.center_clarity = request.form.get('center_clarity')
            listing.center_certification = request.form.get('center_certification')
            
            # Setting details
            listing.metal = request.form.get('metal')
            listing.ring_size = request.form.get('ring_size')
            listing.total_carat_weight = float(request.form.get('total_carat_weight', 0)) if request.form.get('total_carat_weight') else None
            listing.setting_retail_value = float(request.form.get('setting_retail_value', 0)) if request.form.get('setting_retail_value') else None
            
            listing.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('Listing updated successfully!', 'success')
            return redirect(url_for('admin.edit_listing_split', listing_id=listing_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating listing: {str(e)}', 'error')
    
    return render_template('admin/listing_form_split.html', listing=listing)

@admin_bp.route('/listings/new-split', methods=['GET', 'POST'])
@login_required
def new_listing_split():
    """Create new listing with split-screen editor"""
    if request.method == 'POST':
        try:
            listing = Listing(
                title=request.form.get('title'),
                sku=request.form.get('sku'),
                category=request.form.get('category'),
                center_shape=request.form.get('center_shape'),
                retail_value=float(request.form.get('retail_value', 0)),
                sale_price=float(request.form.get('sale_price', 0)),
                description=request.form.get('description'),
                is_active=bool(request.form.get('is_active')),
                
                # Stone details
                center_stone=request.form.get('center_stone'),
                center_carat_weight=float(request.form.get('center_carat_weight', 0)) if request.form.get('center_carat_weight') else None,
                center_color=request.form.get('center_color'),
                center_clarity=request.form.get('center_clarity'),
                center_certification=request.form.get('center_certification'),
                
                # Setting details
                metal=request.form.get('metal'),
                ring_size=request.form.get('ring_size'),
                total_carat_weight=float(request.form.get('total_carat_weight', 0)) if request.form.get('total_carat_weight') else None,
                setting_retail_value=float(request.form.get('setting_retail_value', 0)) if request.form.get('setting_retail_value') else None
            )
            
            db.session.add(listing)
            db.session.commit()
            
            flash('Listing created successfully!', 'success')
            return redirect(url_for('admin.edit_listing_split', listing_id=listing.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating listing: {str(e)}', 'error')
    
    return render_template('admin/listing_form_split.html', listing=None)

@admin_bp.route('/listings/<int:listing_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_listing(listing_id):
    """Edit existing listing"""
    listing = Listing.query.get_or_404(listing_id)
    
    if request.method == 'POST':
        old_category = listing.category
        old_shape = listing.center_shape
        old_sku = listing.sku
        
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
        
        # Handle image uploads if any new ones
        existing_images = json.loads(listing.images) if listing.images else []
        new_images = []
        
        # Create gallery directory for new images
        gallery_path = os.path.join('static/WMD_Photos_NoVideos', listing.category, listing.center_shape, listing.sku)
        os.makedirs(gallery_path, exist_ok=True)
        
        for i in range(10):
            if f'image_{i}' in request.files:
                file = request.files[f'image_{i}']
                if file and file.filename:
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    filename = f"{timestamp}_{i}{file_ext}"
                    upload_path = os.path.join(gallery_path, filename)
                    
                    file.save(upload_path)
                    relative_path = f"/static/WMD_Photos_NoVideos/{listing.category}/{listing.center_shape}/{listing.sku}/{filename}"
                    new_images.append(relative_path)
        
        # Combine existing and new images
        all_images = existing_images + new_images
        if all_images:
            listing.images = json.dumps(all_images)
        
        db.session.commit()
        flash('Listing updated successfully!')
        return redirect(url_for('admin.listings'))
    
    from routes.gallery import JEWELRY_CATEGORIES, DIAMOND_SHAPES
    return render_template('admin/listing_form.html', 
                         listing=listing,
                         gallery_categories=JEWELRY_CATEGORIES,
                         diamond_shapes=DIAMOND_SHAPES)

@admin_bp.route('/listings/<int:listing_id>/delete', methods=['POST'])
@login_required
def delete_listing(listing_id):
    """Delete a listing"""
    listing = Listing.query.get_or_404(listing_id)
    
    # Optionally remove the gallery directory and images
    if listing.category and listing.center_shape and listing.sku:
        gallery_path = os.path.join('static/WMD_Photos_NoVideos', listing.category, listing.center_shape, listing.sku)
        if os.path.exists(gallery_path):
            import shutil
            try:
                shutil.rmtree(gallery_path)
            except:
                pass  # Continue even if directory removal fails
    
    db.session.delete(listing)
    db.session.commit()
    
    flash('Listing deleted successfully!')
    return redirect(url_for('admin.listings'))

@admin_bp.route('/import_gallery', methods=['GET', 'POST'])
@login_required
def import_gallery():
    """Import existing gallery items into listings database"""
    if request.method == 'POST':
        imported_count = 0
        skipped_count = 0
        
        # Scan the WMD_Photos_NoVideos directory
        photos_path = os.path.join('static/WMD_Photos_NoVideos')
        
        if os.path.exists(photos_path):
            for category in os.listdir(photos_path):
                category_path = os.path.join(photos_path, category)
                if os.path.isdir(category_path):
                    for shape in os.listdir(category_path):
                        shape_path = os.path.join(category_path, shape)
                        if os.path.isdir(shape_path):
                            for item in os.listdir(shape_path):
                                item_path = os.path.join(shape_path, item)
                                if os.path.isdir(item_path):
                                    # Check if listing already exists
                                    existing = Listing.query.filter_by(
                                        category=category,
                                        center_shape=shape,
                                        sku=item
                                    ).first()
                                    
                                    if existing:
                                        skipped_count += 1
                                        continue
                                    
                                    # Get images
                                    images = []
                                    for file in os.listdir(item_path):
                                        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                                            images.append(f"/static/WMD_Photos_NoVideos/{category}/{shape}/{item}/{file}")
                                    
                                    if images:
                                        # Create new listing
                                        listing = Listing(
                                            title=f"{shape} {category} - {item}",
                                            sku=item,
                                            category=category,
                                            center_shape=shape,
                                            retail_value=0.00,  # Default values
                                            sale_price=0.00,
                                            description=f"Imported {shape} {category.lower()} from gallery",
                                            images=json.dumps(images),
                                            is_active=True
                                        )
                                        
                                        db.session.add(listing)
                                        imported_count += 1
            
            db.session.commit()
            flash(f'Gallery import completed! Imported {imported_count} items, skipped {skipped_count} existing items.')
        else:
            flash('Gallery photos directory not found!')
        
        return redirect(url_for('admin.listings'))
    
    # GET request - show import form
    existing_count = Listing.query.count()
    return render_template('admin/import_gallery.html', existing_count=existing_count)

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

# Image management routes
@admin_bp.route('/listings/<int:listing_id>/images')
@login_required
def manage_images(listing_id):
    """Manage images for a specific listing"""
    listing = Listing.query.get_or_404(listing_id)
    return render_template('admin/manage_images.html', listing=listing)

@admin_bp.route('/listings/<int:listing_id>/images/add', methods=['POST'])
@login_required
def add_image(listing_id):
    """Add a new image to a listing"""
    listing = Listing.query.get_or_404(listing_id)
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename:
        # Create gallery directory structure
        gallery_path = os.path.join('static/WMD_Photos_NoVideos', listing.category, listing.center_shape, listing.sku)
        os.makedirs(gallery_path, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        file_ext = os.path.splitext(secure_filename(file.filename))[1].lower()
        filename = f"{timestamp}{file_ext}"
        
        # Save file
        file_path = os.path.join(gallery_path, filename)
        file.save(file_path)
        
        # Create image record
        relative_url = f"/static/WMD_Photos_NoVideos/{listing.category}/{listing.center_shape}/{listing.sku}/{filename}"
        
        # Get next order number
        max_order = db.session.query(db.func.max(ListingImage.display_order)).filter_by(listing_id=listing_id).scalar() or 0
        
        image = ListingImage(
            listing_id=listing_id,
            image_url=relative_url,
            image_path=file_path,
            display_order=max_order + 1,
            alt_text=request.form.get('alt_text', ''),
            caption=request.form.get('caption', '')
        )
        
        db.session.add(image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'image': {
                'id': image.id,
                'url': image.image_url,
                'alt_text': image.alt_text,
                'caption': image.caption,
                'display_order': image.display_order,
                'is_thumbnail': image.is_thumbnail
            }
        })
    
    return jsonify({'error': 'Invalid file'}), 400

@admin_bp.route('/listings/<int:listing_id>/images/<int:image_id>/delete', methods=['DELETE'])
@login_required
def delete_image(listing_id, image_id):
    """Delete an image from a listing"""
    image = ListingImage.query.filter_by(id=image_id, listing_id=listing_id).first_or_404()
    
    # Delete physical file if it exists
    if image.image_path and os.path.exists(image.image_path):
        try:
            os.remove(image.image_path)
        except:
            pass  # Continue even if file deletion fails
    
    db.session.delete(image)
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/listings/<int:listing_id>/images/reorder', methods=['POST'])
@login_required
def reorder_images(listing_id):
    """Reorder images for a listing"""
    listing = Listing.query.get_or_404(listing_id)
    
    image_ids = request.json.get('image_ids', [])
    
    for index, image_id in enumerate(image_ids):
        image = ListingImage.query.filter_by(id=image_id, listing_id=listing_id).first()
        if image:
            image.display_order = index
    
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/listings/<int:listing_id>/images/<int:image_id>/set-thumbnail', methods=['POST'])
@login_required
def set_thumbnail(listing_id, image_id):
    """Set an image as the thumbnail for a listing"""
    listing = Listing.query.get_or_404(listing_id)
    
    # Remove thumbnail flag from all images for this listing
    ListingImage.query.filter_by(listing_id=listing_id).update({'is_thumbnail': False})
    
    # Set the selected image as thumbnail
    image = ListingImage.query.filter_by(id=image_id, listing_id=listing_id).first_or_404()
    image.is_thumbnail = True
    
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/listings/<int:listing_id>/images/<int:image_id>/update', methods=['POST'])
@login_required
def update_image(listing_id, image_id):
    """Update image metadata"""
    image = ListingImage.query.filter_by(id=image_id, listing_id=listing_id).first_or_404()
    
    image.alt_text = request.form.get('alt_text', '')
    image.caption = request.form.get('caption', '')
    image.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/migrate-legacy-images', methods=['POST'])
@login_required
def migrate_legacy_images():
    """Migrate images from legacy JSON format to new ListingImage model"""
    migrated_count = 0
    error_count = 0
    
    listings = Listing.query.filter(Listing.images.isnot(None)).all()
    
    for listing in listings:
        if listing.listing_images:
            continue  # Skip if already has new format images
            
        legacy_images = listing.get_legacy_images()
        if legacy_images:
            for index, image_url in enumerate(legacy_images):
                try:
                    # Create new ListingImage record
                    listing_image = ListingImage(
                        listing_id=listing.id,
                        image_url=image_url,
                        display_order=index,
                        is_thumbnail=(index == 0),  # First image is thumbnail
                        alt_text=f"{listing.title} - Image {index + 1}"
                    )
                    
                    db.session.add(listing_image)
                    migrated_count += 1
                except Exception as e:
                    error_count += 1
                    continue
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'migrated': migrated_count,
            'errors': error_count,
            'message': f'Successfully migrated {migrated_count} images with {error_count} errors'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Migration failed: {str(e)}'}), 500

@admin_bp.route('/listings/<int:listing_id>/images/<int:image_id>/edit', methods=['POST'])
@login_required
def edit_image(listing_id, image_id):
    """Save an edited image"""
    image = ListingImage.query.filter_by(id=image_id, listing_id=listing_id).first_or_404()
    
    data = request.get_json()
    if not data or 'edited_image' not in data:
        return jsonify({'error': 'No edited image data provided'}), 400
    
    try:
        # Parse the base64 image data
        image_data = data['edited_image']
        if image_data.startswith('data:image'):
            # Remove the data URL prefix
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Open and process the image with PIL
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary (for JPEG compatibility)
        if pil_image.mode in ('RGBA', 'LA', 'P'):
            pil_image = pil_image.convert('RGB')
        
        # Generate unique filename for edited version
        listing = Listing.query.get_or_404(listing_id)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"edited_{timestamp}_{unique_id}.jpg"
        
        # Create directory structure
        gallery_path = os.path.join('static/WMD_Photos_NoVideos', listing.category, listing.center_shape, listing.sku)
        os.makedirs(gallery_path, exist_ok=True)
        
        # Save the edited image
        file_path = os.path.join(gallery_path, filename)
        pil_image.save(file_path, 'JPEG', quality=90, optimize=True)
        
        # Create new URL
        new_url = f"/static/WMD_Photos_NoVideos/{listing.category}/{listing.center_shape}/{listing.sku}/{filename}"
        
        # Update the image record with the new URL
        # Keep original for potential rollback, update current URL
        image.image_url = new_url
        image.image_path = file_path
        image.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_url': new_url,
            'message': 'Image edited and saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process edited image: {str(e)}'}), 500

@admin_bp.route('/listings/<int:listing_id>/images/<int:image_id>/versions', methods=['GET'])
@login_required
def get_image_versions(listing_id, image_id):
    """Get all versions of an image"""
    image = ListingImage.query.filter_by(id=image_id, listing_id=listing_id).first_or_404()
    
    # For now, return the current version
    # In future, could track version history
    versions = [{
        'id': 'current',
        'url': image.image_url,
        'created_at': image.updated_at.isoformat(),
        'is_current': True
    }]
    
    return jsonify({
        'success': True,
        'versions': versions
    })

@admin_bp.route('/listings/<int:listing_id>/images/<int:image_id>/restore', methods=['POST'])
@login_required
def restore_image_version(listing_id, image_id):
    """Restore a previous version of an image"""
    # Placeholder for future version restoration functionality
    return jsonify({
        'success': False,
        'message': 'Version restoration not yet implemented'
    })

@admin_bp.route('/listings/<int:listing_id>/images/<int:image_id>/editor')
@login_required
def image_editor(listing_id, image_id):
    """Windows 10 style image editor"""
    listing = Listing.query.get_or_404(listing_id)
    image = ListingImage.query.filter_by(id=image_id, listing_id=listing_id).first_or_404()
    
    return render_template('admin/win10_image_editor.html', 
                         listing=listing, 
                         image_id=image_id, 
                         image_url=image.image_url) 