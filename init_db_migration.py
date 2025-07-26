#!/usr/bin/env python3
"""
Database migration script for WantMyDiamond image management system.
This script creates the new ListingImage table and migrates existing images.
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Listing, ListingImage

def create_tables():
    """Create new database tables"""
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
        print("✓ Tables created successfully")

def migrate_legacy_images():
    """Migrate existing images from JSON format to ListingImage model"""
    print("Migrating legacy images...")
    
    with app.app_context():
        migrated_count = 0
        error_count = 0
        
        # Get all listings with legacy images
        listings = Listing.query.filter(Listing.images.isnot(None)).all()
        
        for listing in listings:
            # Skip if already has new format images
            if listing.listing_images:
                print(f"Skipping {listing.sku} - already has new format images")
                continue
                
            legacy_images = listing.get_legacy_images()
            if legacy_images:
                print(f"Migrating {len(legacy_images)} images for {listing.sku}")
                
                for index, image_url in enumerate(legacy_images):
                    try:
                        # Extract file path from URL if possible
                        image_path = None
                        if image_url.startswith('/static/'):
                            image_path = image_url[1:]  # Remove leading slash
                        
                        # Create new ListingImage record
                        listing_image = ListingImage(
                            listing_id=listing.id,
                            image_url=image_url,
                            image_path=image_path,
                            display_order=index,
                            is_thumbnail=(index == 0),  # First image is thumbnail
                            alt_text=f"{listing.title} - Image {index + 1}",
                            caption=f"Image {index + 1} of {listing.title}"
                        )
                        
                        db.session.add(listing_image)
                        migrated_count += 1
                        
                    except Exception as e:
                        print(f"Error migrating image {image_url} for listing {listing.sku}: {e}")
                        error_count += 1
                        continue
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"✓ Migration completed: {migrated_count} images migrated, {error_count} errors")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            return False
        
        return True

def verify_migration():
    """Verify the migration was successful"""
    print("Verifying migration...")
    
    with app.app_context():
        total_listings = Listing.query.count()
        listings_with_new_images = Listing.query.join(ListingImage).count()
        listings_with_legacy_images = Listing.query.filter(Listing.images.isnot(None)).count()
        total_images = ListingImage.query.count()
        
        print(f"Total listings: {total_listings}")
        print(f"Listings with new format images: {listings_with_new_images}")
        print(f"Listings with legacy images: {listings_with_legacy_images}")
        print(f"Total images in new format: {total_images}")
        
        # Check for thumbnails
        thumbnails = ListingImage.query.filter_by(is_thumbnail=True).count()
        print(f"Listings with designated thumbnails: {thumbnails}")
        
        print("✓ Migration verification completed")

def backup_legacy_data():
    """Create a backup of legacy image data before migration"""
    print("Creating backup of legacy image data...")
    
    with app.app_context():
        backup_data = []
        listings = Listing.query.filter(Listing.images.isnot(None)).all()
        
        for listing in listings:
            if listing.images:
                backup_data.append({
                    'listing_id': listing.id,
                    'sku': listing.sku,
                    'title': listing.title,
                    'legacy_images': listing.images
                })
        
        # Save backup to file
        backup_filename = f"image_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_filename, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"✓ Backup created: {backup_filename}")
        return backup_filename

def main():
    """Run the complete migration process"""
    print("WantMyDiamond Image Management Migration")
    print("=" * 40)
    
    # Step 1: Create backup
    backup_file = backup_legacy_data()
    
    # Step 2: Create new tables
    create_tables()
    
    # Step 3: Migrate legacy images
    success = migrate_legacy_images()
    
    if success:
        # Step 4: Verify migration
        verify_migration()
        
        print("\n" + "=" * 40)
        print("Migration completed successfully!")
        print(f"Backup file created: {backup_file}")
        print("\nYou can now:")
        print("1. Use the admin panel to manage images with drag-and-drop")
        print("2. Set custom thumbnails for each listing")
        print("3. Add/remove images from listings")
        print("4. Reorder images as needed")
        print("\nThe legacy 'images' field is preserved for rollback if needed.")
    else:
        print("\n" + "=" * 40)
        print("Migration failed! Please check the errors above.")
        print(f"Legacy data backup is available in: {backup_file}")

if __name__ == "__main__":
    main() 