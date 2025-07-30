from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from models import db, Listing, Contact, Message, CustomRequest, AppraisalRequest
import json
import os
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@main_bp.route('/gallery')
def gallery():
    """Gallery page showing all jewelry listings"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)
    
    query = Listing.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    
    listings = query.paginate(
        page=page, per_page=12, error_out=False
    )
    
    categories = db.session.query(Listing.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('gallery.html', listings=listings, categories=categories, current_category=category)

@main_bp.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    """Individual listing page with customization options"""
    listing = Listing.query.get_or_404(listing_id)
    
    # Parse customization options from JSON
    customization_options = {}
    if listing.options:
        try:
            customization_options = json.loads(listing.options)
        except:
            customization_options = {}
    
    return render_template('listing_detail.html', listing=listing, options=customization_options)

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact form and messaging entry point"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        # Check if contact exists
        contact = Contact.query.filter_by(email=email).first()
        if not contact:
            contact = Contact(name=name, email=email, phone=phone)
            db.session.add(contact)
            db.session.commit()
        
        # Store contact ID in session
        session['contact_id'] = contact.id
        
        # Check if this is from a listing customization
        listing_data = request.form.get('listing_customization')
        if listing_data:
            # Create initial message with customization details
            message = Message(
                contact_id=contact.id,
                sender_type='customer',
                content=f"Hi! I'm interested in customizing the following item:",
                listing_customization=listing_data
            )
            db.session.add(message)
            db.session.commit()
        
        return redirect(url_for('main.messages'))
    
    # Handle GET request - check for auto-redirect from gallery
    email = request.args.get('email')
    auto_redirect = request.args.get('auto_redirect')
    
    if email and auto_redirect:
        # Find the contact and set up session
        contact = Contact.query.filter_by(email=email).first()
        if contact:
            session['contact_id'] = contact.id
            flash('Your inquiry has been received! You can continue the conversation below.', 'success')
            return redirect(url_for('main.messages'))
    
    return render_template('contact.html')

@main_bp.route('/messages')
def messages():
    """Messaging interface"""
    contact_id = session.get('contact_id')
    if not contact_id:
        return redirect(url_for('main.contact'))
    
    contact = Contact.query.get_or_404(contact_id)
    messages = Message.query.filter_by(contact_id=contact_id).order_by(Message.created_at.asc()).all()
    
    return render_template('messages.html', contact=contact, messages=messages)

@main_bp.route('/send_message', methods=['POST'])
def send_message():
    """Send a new message"""
    contact_id = session.get('contact_id')
    if not contact_id:
        return jsonify({'error': 'Not authorized'}), 401
    
    content = request.form.get('content')
    if not content:
        return jsonify({'error': 'Message content required'}), 400
    
    message = Message(
        contact_id=contact_id,
        sender_type='customer',
        content=content
    )
    
    # Handle file upload
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            filename = secure_filename(file.filename)
            # In production, upload to S3 or similar
            upload_path = os.path.join('static/uploads', filename)
            file.save(upload_path)
            message.attachment_url = upload_path
            
            # Determine file type
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                message.attachment_type = 'image'
            elif filename.lower().endswith(('.mp4', '.mov', '.avi')):
                message.attachment_type = 'video'
            else:
                message.attachment_type = 'file'
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({'success': True})

@main_bp.route('/custom_request', methods=['GET', 'POST'])
def custom_request():
    """Custom jewelry request page"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        title = request.form.get('title')
        description = request.form.get('description')
        budget_range = request.form.get('budget_range')
        
        # Check if contact exists
        contact = Contact.query.filter_by(email=email).first()
        if not contact:
            contact = Contact(name=name, email=email, phone=phone)
            db.session.add(contact)
            db.session.commit()
        
        # Create custom request
        custom_req = CustomRequest(
            contact_id=contact.id,
            title=title,
            description=description,
            budget_range=budget_range
        )
        
        # Handle image uploads
        reference_images = []
        for i in range(5):  # Allow up to 5 images
            if f'image_{i}' in request.files:
                file = request.files[f'image_{i}']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join('static/uploads', filename)
                    file.save(upload_path)
                    reference_images.append(upload_path)
        
        if reference_images:
            custom_req.reference_images = json.dumps(reference_images)
        
        # Handle reference links
        links = []
        for i in range(3):  # Allow up to 3 links
            link = request.form.get(f'link_{i}')
            if link:
                links.append(link)
        
        if links:
            custom_req.reference_links = json.dumps(links)
        
        db.session.add(custom_req)
        db.session.commit()
        
        flash('Your custom request has been submitted! We will contact you soon.')
        return redirect(url_for('main.index'))
    
    return render_template('custom_request.html')

@main_bp.route('/appraisal', methods=['GET', 'POST'])
def appraisal():
    """DIA appraisal service page"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        item_description = request.form.get('item_description')
        appraisal_purpose = request.form.get('appraisal_purpose')
        
        # Check if contact exists
        contact = Contact.query.filter_by(email=email).first()
        if not contact:
            contact = Contact(name=name, email=email, phone=phone)
            db.session.add(contact)
            db.session.commit()
        
        # Create appraisal request
        appraisal_req = AppraisalRequest(
            contact_id=contact.id,
            item_description=item_description,
            appraisal_purpose=appraisal_purpose
        )
        
        # Handle image uploads
        item_images = []
        for i in range(5):  # Allow up to 5 images
            if f'image_{i}' in request.files:
                file = request.files[f'image_{i}']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join('static/uploads', filename)
                    file.save(upload_path)
                    item_images.append(upload_path)
        
        if item_images:
            appraisal_req.item_images = json.dumps(item_images)
        
        db.session.add(appraisal_req)
        db.session.commit()
        
        flash('Your appraisal request has been submitted! We will contact you with payment instructions.')
        return redirect(url_for('main.index'))
    
    return render_template('appraisal.html')

@main_bp.route('/customize_listing', methods=['POST'])
def customize_listing():
    """Handle listing customization from detail page"""
    listing_id = request.form.get('listing_id')
    customizations = {}
    
    # Collect all form data as customizations
    for key, value in request.form.items():
        if key != 'listing_id' and value:
            customizations[key] = value
    
    # Store customization data to pass to contact form
    customization_data = {
        'listing_id': listing_id,
        'customizations': customizations
    }
    
    session['pending_customization'] = json.dumps(customization_data)
    return redirect(url_for('main.contact'))

@main_bp.route('/find_messages', methods=['POST'])
def find_messages():
    """Find existing messages by contact info"""
    email = request.form.get('email')
    contact = Contact.query.filter_by(email=email).first()
    
    if contact:
        session['contact_id'] = contact.id
        return redirect(url_for('main.messages'))
    else:
        flash('No messages found for this email address.')
        return redirect(url_for('main.contact')) 