import os
from flask import Blueprint, render_template, jsonify, request, current_app
from werkzeug.utils import secure_filename
import json

# Import the Listing model
from models import Listing

gallery_bp = Blueprint('gallery', __name__)

# Jewelry categories mapping
JEWELRY_CATEGORIES = {
    'Engagement Ring': {
        'name': 'Engagement Rings',
        'stone_config': 'center_and_side',
        'description': 'Elegant engagement rings with center stones and optional side stones'
    },
    'Bridal Set': {
        'name': 'Bridal Sets',
        'stone_config': 'center_and_side',
        'description': 'Complete bridal sets with matching engagement and wedding bands'
    },
    'Eternity Bands': {
        'name': 'Eternity Bands',
        'stone_config': 'side_only',
        'description': 'Continuous band rings with stones around the entire band'
    },
    'Earrings': {
        'name': 'Earrings',
        'stone_config': 'center_only',
        'description': 'Beautiful earrings with center stones'
    },
    'Bracelets': {
        'name': 'Bracelets',
        'stone_config': 'side_only',
        'description': 'Elegant bracelets with continuous stone settings'
    }
}

# Ring size options (3.0 to 12.5 in 0.25 increments)
RING_SIZES = [str(round(size * 0.25 + 3.0, 2)).rstrip('0').rstrip('.') for size in range(39)]

# Metal options
METAL_OPTIONS = {
    '14k_gold': {
        'name': '14K Gold',
        'finishes': ['White', 'Yellow', 'Rose', '2-Tone']
    },
    '18k_gold': {
        'name': '18K Gold', 
        'finishes': ['White', 'Yellow', 'Rose', '2-Tone']
    },
    '19k_gold': {
        'name': '19K Gold',
        'finishes': ['White', 'Yellow', 'Rose', '2-Tone']
    },
    'platinum': {
        'name': 'Platinum',
        'finishes': ['Platinum']
    },
    'palladium': {
        'name': 'Palladium',
        'finishes': ['Palladium']
    }
}

# Diamond color grades with sample descriptions
DIAMOND_COLORS = {
    'D': {'name': 'D - Colorless', 'description': 'Absolutely colorless'},
    'E': {'name': 'E - Colorless', 'description': 'Colorless'},
    'F': {'name': 'F - Colorless', 'description': 'Colorless'},
    'G': {'name': 'G - Near Colorless', 'description': 'Near colorless'},
    'H': {'name': 'H - Near Colorless', 'description': 'Near colorless'},
    'I': {'name': 'I - Near Colorless', 'description': 'Near colorless'},
    'J': {'name': 'J - Near Colorless', 'description': 'Near colorless'},
    'K': {'name': 'K - Faint', 'description': 'Faint yellow'},
    'L': {'name': 'L - Faint', 'description': 'Faint yellow'},
    'M': {'name': 'M - Faint', 'description': 'Faint yellow'}
}

# Diamond clarity grades
DIAMOND_CLARITY = {
    'FL': {'name': 'FL - Flawless', 'description': 'No inclusions visible under 10x magnification'},
    'IF': {'name': 'IF - Internally Flawless', 'description': 'No inclusions visible under 10x magnification'},
    'VVS1': {'name': 'VVS1', 'description': 'Very Very Slightly Included'},
    'VVS2': {'name': 'VVS2', 'description': 'Very Very Slightly Included'},
    'VS1': {'name': 'VS1', 'description': 'Very Slightly Included'},
    'VS2': {'name': 'VS2', 'description': 'Very Slightly Included'},
    'SI1': {'name': 'SI1', 'description': 'Slightly Included'},
    'SI2': {'name': 'SI2', 'description': 'Slightly Included'},
    'I1': {'name': 'I1', 'description': 'Included'},
    'I2': {'name': 'I2', 'description': 'Included'},
    'I3': {'name': 'I3', 'description': 'Included'}
}

# Diamond shapes
DIAMOND_SHAPES = [
    'Round', 'Princess', 'Cushion', 'Emerald', 'Oval', 'Radiant', 
    'Asscher', 'Marquise', 'Heart', 'Pear'
]

# Diamond cuts
DIAMOND_CUTS = [
    'Excellent', 'Very Good', 'Good', 'Fair', 'Poor'
]

def get_photo_structure():
    """Get the gallery structure from active listings in the database"""
    structure = {}
    
    # Get all active listings from the database
    active_listings = Listing.query.filter_by(is_active=True).all()
    
    for listing in active_listings:
        category = listing.category
        shape = listing.center_shape
        sku = listing.sku
        
        # Skip if missing required fields
        if not category or not shape or not sku:
            continue
            
        # Initialize category if not exists
        if category not in structure:
            structure[category] = {}
            
        # Initialize shape if not exists
        if shape not in structure[category]:
            structure[category][shape] = []
            
        # Get images from listing
        images = []
        if listing.images:
            try:
                images = json.loads(listing.images)
            except:
                images = []
        
        # Create item data structure
        item_data = {
            'sku': sku,
            'title': listing.title,
            'images': images,
            'thumbnail': images[0] if images else None,
            'listing_id': listing.id,
            'description': listing.description or '',
            'retail_value': listing.retail_value,
            'sale_price': listing.sale_price
        }
        
        structure[category][shape].append(item_data)
    
    return structure

@gallery_bp.route('/')
def index():
    """Main gallery page showing all categories"""
    photo_structure = get_photo_structure()
    return render_template('gallery/index.html', 
                         categories=JEWELRY_CATEGORIES,
                         photo_structure=photo_structure)

@gallery_bp.route('/category/<category_name>')
def category_view(category_name):
    """View all items in a specific category"""
    photo_structure = get_photo_structure()
    
    if category_name not in photo_structure:
        return render_template('404.html'), 404
    
    category_data = JEWELRY_CATEGORIES.get(category_name, {})
    items = []
    
    for shape, shape_items in photo_structure[category_name].items():
        items.extend(shape_items)
    
    return render_template('gallery/category.html',
                         category_name=category_name,
                         category_data=category_data,
                         items=items,
                         shapes=list(photo_structure[category_name].keys()),
                         photo_structure=photo_structure[category_name])

@gallery_bp.route('/item/<category_name>/<shape>/<sku>')
def item_detail(category_name, shape, sku):
    """Detailed view of a specific jewelry item"""
    # Get the listing from the database
    listing = Listing.query.filter_by(
        category=category_name, 
        center_shape=shape, 
        sku=sku, 
        is_active=True
    ).first()
    
    if not listing:
        return render_template('404.html'), 404
    
    # Get images from listing
    images = []
    if listing.images:
        try:
            images = json.loads(listing.images)
        except:
            images = []
    
    # Create item data structure
    item = {
        'sku': listing.sku,
        'title': listing.title,
        'images': images,
        'thumbnail': images[0] if images else None,
        'listing_id': listing.id,
        'description': listing.description or '',
        'retail_value': listing.retail_value,
        'sale_price': listing.sale_price
    }
    
    category_data = JEWELRY_CATEGORIES.get(category_name, {})
    
    return render_template('gallery/item_detail.html',
                         item=item,
                         category_name=category_name,
                         category_data=category_data,
                         shape=shape,
                         ring_sizes=RING_SIZES,
                         metal_options=METAL_OPTIONS,
                         diamond_colors=DIAMOND_COLORS,
                         diamond_clarity=DIAMOND_CLARITY,
                         diamond_shapes=DIAMOND_SHAPES,
                         diamond_cuts=DIAMOND_CUTS)

@gallery_bp.route('/api/customize', methods=['POST'])
def customize_item():
    """Handle customization requests"""
    data = request.get_json()
    
    # Here you would process the customization options
    # For now, just return the received data
    return jsonify({
        'status': 'success',
        'message': 'Customization options received',
        'data': data
    })

@gallery_bp.route('/api/request-info', methods=['POST'])
def request_info():
    """Handle information requests"""
    from models import db, Contact, Message
    from datetime import datetime
    
    data = request.get_json()
    
    # Extract form data
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    message_content = data.get('message', '')
    
    # Extract item and customization data
    item_sku = data.get('item_sku')
    item_title = data.get('item_title')
    category = data.get('category')
    shape = data.get('shape')
    customizations = data.get('customizations', {})
    
    if not name or not email:
        return jsonify({
            'status': 'error',
            'message': 'Name and email are required'
        }), 400
    
    try:
        # Check if contact exists, create if not
        contact = Contact.query.filter_by(email=email).first()
        if not contact:
            contact = Contact(
                name=name,
                email=email,
                phone=phone,
                created_at=datetime.utcnow()
            )
            db.session.add(contact)
            db.session.flush()  # Get the contact ID
        
        # Create the inquiry message
        inquiry_text = f"Hi! I'm interested in learning more about this item:"
        if message_content:
            inquiry_text += f"\n\nMessage: {message_content}"
        
        # Create message with customization data
        customization_data = {
            'item_sku': item_sku,
            'item_title': item_title,
            'category': category,
            'shape': shape,
            'customizations': customizations
        }
        
        message = Message(
            contact_id=contact.id,
            sender_type='customer',
            content=inquiry_text,
            listing_customization=json.dumps(customization_data),
            created_at=datetime.utcnow()
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Your inquiry has been received! Redirecting to messages...',
            'contact_id': contact.id,
            'redirect_url': f'/contact?email={email}&auto_redirect=true'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'There was an error processing your request. Please try again.'
        }), 500 