#!/usr/bin/env python3
"""Test script to see what Copart actually returns"""
from scraper import CopartScraper
import json

print("Testing Copart scraper...")
scraper = CopartScraper()

try:
    vehicles = scraper.search_copart(
        make="Toyota",
        model="Corolla",
        years=[2017, 2018, 2019, 2020],
        locations=["MD", "NJ", "DC"],
        limit=5  # Just get 5 for testing
    )
    
    print(f"\nFound {len(vehicles)} vehicles")
    if vehicles:
        print("\nFirst vehicle:")
        print(json.dumps(vehicles[0], indent=2))
    else:
        print("No vehicles found!")
        
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    scraper.close()
