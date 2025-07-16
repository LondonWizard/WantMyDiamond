from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from models import db, Listing, Contact, Message, CustomRequest, AppraisalRequest
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/listings')
def get_listings():
    """Get listings as JSON for AJAX requests"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)
    search = request.args.get('search', None)
    
    query = Listing.query.filter_by(is_active=True)
    
    if category:
        query = query.filter(Listing.category == category)
    
    if search:
        query = query.filter(Listing.title.contains(search) | 
                           Listing.description.contains(search))
    
    listings = query.paginate(page=page, per_page=12, error_out=False)
    
    result = {
        'listings': [],
        'has_next': listings.has_next,
        'has_prev': listings.has_prev,
        'page': listings.page,
        'pages': listings.pages,
        'total': listings.total
    }
    
    for listing in listings.items:
        images = []
        if listing.images:
            try:
                images = json.loads(listing.images)
            except:
                images = []
        
        result['listings'].append({
            'id': listing.id,
            'title': listing.title,
            'sku': listing.sku,
            'category': listing.category,
            'retail_value': listing.retail_value,
            'sale_price': listing.sale_price,
            'images': images,
            'description': listing.description[:200] + '...' if listing.description and len(listing.description) > 200 else listing.description
        })
    
    return jsonify(result)

@api_bp.route('/listing/<int:listing_id>')
def get_listing(listing_id):
    """Get single listing details as JSON"""
    listing = Listing.query.get_or_404(listing_id)
    
    images = []
    options = {}
    
    if listing.images:
        try:
            images = json.loads(listing.images)
        except:
            images = []
    
    if listing.options:
        try:
            options = json.loads(listing.options)
        except:
            options = {}
    
    result = {
        'id': listing.id,
        'title': listing.title,
        'sku': listing.sku,
        'category': listing.category,
        'retail_value': listing.retail_value,
        'sale_price': listing.sale_price,
        'description': listing.description,
        'images': images,
        'options': options,
        'center_stone': {
            'stone': listing.center_stone,
            'shape': listing.center_shape,
            'carat_weight': listing.center_carat_weight,
            'color': listing.center_color,
            'clarity': listing.center_clarity,
            'certification': listing.center_certification
        },
        'secondary_stone': {
            'shape': listing.secondary_shape,
            'carat_weight': listing.secondary_carat_weight,
            'color': listing.secondary_color,
            'clarity': listing.secondary_clarity
        },
        'setting': {
            'total_carat_weight': listing.total_carat_weight,
            'metal': listing.metal,
            'ring_size': listing.ring_size,
            'retail_value': listing.setting_retail_value
        }
    }
    
    return jsonify(result)

@api_bp.route('/messages/unread_count')
def get_unread_messages():
    """Get count of unread messages for current contact"""
    contact_id = session.get('contact_id')
    if not contact_id:
        return jsonify({'count': 0})
    
    count = Message.query.filter_by(
        contact_id=contact_id, 
        sender_type='admin',
        is_read=False
    ).count()
    
    return jsonify({'count': count})

@api_bp.route('/messages/mark_read', methods=['POST'])
def mark_messages_read():
    """Mark messages as read for current contact"""
    contact_id = session.get('contact_id')
    if not contact_id:
        return jsonify({'error': 'Not authorized'}), 401
    
    Message.query.filter_by(
        contact_id=contact_id,
        sender_type='admin',
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/admin/stats')
@login_required
def admin_stats():
    """Get admin dashboard statistics"""
    if not current_user.is_admin:
        return jsonify({'error': 'Not authorized'}), 401
    
    stats = {
        'total_listings': Listing.query.count(),
        'active_listings': Listing.query.filter_by(is_active=True).count(),
        'total_messages': Message.query.count(),
        'unread_messages': Message.query.filter_by(is_read=False, sender_type='customer').count(),
        'pending_custom_requests': CustomRequest.query.filter_by(status='pending').count(),
        'pending_appraisals': AppraisalRequest.query.filter_by(status='pending').count(),
        'total_contacts': Contact.query.count()
    }
    
    return jsonify(stats)

@api_bp.route('/admin/messages/recent')
@login_required
def recent_messages():
    """Get recent messages for admin dashboard"""
    if not current_user.is_admin:
        return jsonify({'error': 'Not authorized'}), 401
    
    messages = Message.query.filter_by(sender_type='customer')\
        .order_by(Message.created_at.desc())\
        .limit(10).all()
    
    result = []
    for msg in messages:
        result.append({
            'id': msg.id,
            'contact_name': msg.contact.name,
            'contact_email': msg.contact.email,
            'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
            'created_at': msg.created_at.isoformat(),
            'is_read': msg.is_read
        })
    
    return jsonify(result)

@api_bp.route('/search_suggestions')
def search_suggestions():
    """Get search suggestions for autocomplete"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    # Search in titles and categories
    titles = db.session.query(Listing.title)\
        .filter(Listing.title.contains(query), Listing.is_active == True)\
        .distinct().limit(5).all()
    
    categories = db.session.query(Listing.category)\
        .filter(Listing.category.contains(query), Listing.is_active == True)\
        .distinct().limit(3).all()
    
    suggestions = []
    for title in titles:
        suggestions.append({'type': 'title', 'value': title[0]})
    
    for category in categories:
        suggestions.append({'type': 'category', 'value': category[0]})
    
    return jsonify(suggestions)

@api_bp.route('/categories')
def get_categories():
    """Get all available categories"""
    categories = db.session.query(Listing.category)\
        .filter(Listing.is_active == True)\
        .distinct().all()
    
    result = [cat[0] for cat in categories]
    return jsonify(result)

@api_bp.route('/validate_email', methods=['POST'])
def validate_email():
    """Check if email exists in contacts"""
    email = request.json.get('email', '').strip()
    if not email:
        return jsonify({'exists': False})
    
    contact = Contact.query.filter_by(email=email).first()
    return jsonify({'exists': bool(contact)}) 