#!/usr/bin/env python3
"""Quick script to show scraped images"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from scraper import scrape_copart_corolla
    
    print("🚗 Running scraper to get images...")
    print("=" * 80)
    
    # Run scraper with limit of 5 cars for quick test
    vehicles = scrape_copart_corolla(limit=5)
    
    if not vehicles:
        print("\n⚠️  No vehicles found!")
        print("This could mean:")
        print("  - No vehicles match the criteria")
        print("  - Page structure changed")
        print("  - Browser/scraper issue")
        sys.exit(1)
    
    print(f"\n✅ Found {len(vehicles)} vehicles!")
    print("=" * 80)
    print("\n📸 IMAGES FOR EACH CAR:")
    print("=" * 80)
    
    for i, vehicle in enumerate(vehicles, 1):
        lot_number = vehicle.get("lot_number", "N/A")
        year = vehicle.get("year", "N/A")
        make = vehicle.get("make", "")
        model = vehicle.get("model", "")
        location = vehicle.get("location", "N/A")
        odometer = vehicle.get("odometer", "N/A")
        images = vehicle.get("images", [])
        
        print(f"\n{'='*80}")
        print(f"🚗 CAR #{i}")
        print(f"{'='*80}")
        print(f"Lot Number: {lot_number}")
        print(f"Vehicle: {year} {make} {model}")
        print(f"Location: {location}")
        print(f"Odometer: {odometer}")
        print(f"Total Images: {len(images)}")
        
        if images:
            print(f"\n📸 IMAGE LINKS ({len(images)} images):")
            for idx, img_url in enumerate(images, 1):
                print(f"   {idx}. {img_url}")
        else:
            print("\n⚠️  No images found for this vehicle")
        
        print(f"{'='*80}")
    
    print(f"\n✅ Displayed {len(vehicles)} cars with their images")
    
except KeyboardInterrupt:
    print("\n\n⚠️  Scraping interrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
