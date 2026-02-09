"""
Copart Toyota Corolla Scraper
Scrapes vehicle data from bid.cars and Copart with strict filtering
Uses Playwright for better cloud deployment support
"""
import time
import re
import os
from playwright.sync_api import sync_playwright, Browser, Page
from bs4 import BeautifulSoup


class CopartScraper:
    """Main scraper class for Copart vehicles"""
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None
        # Don't initialize browser on creation - do it lazily when needed
    
    def setup_browser(self):
        """Setup Playwright browser with Browserless or local browser"""
        try:
            print("Initializing Playwright...")
            self.playwright = sync_playwright().start()
            
            # Check for Browserless configuration
            browserless_url = os.environ.get('BROWSERLESS_URL', None)
            browserless_token = os.environ.get('BROWSERLESS_TOKEN', None)
            
            if browserless_url:
                # Connect to Browserless service
                print(f"🔗 Connecting to Browserless at {browserless_url}...")
                
                # Build WebSocket URL with token if provided
                ws_url = browserless_url
                if browserless_token:
                    # Add token to URL if not already present
                    if '?' not in ws_url:
                        ws_url = f"{ws_url}?token={browserless_token}"
                    elif 'token=' not in ws_url:
                        ws_url = f"{ws_url}&token={browserless_token}"
                
                try:
                    # Connect to Browserless via CDP (Chrome DevTools Protocol)
                    self.browser = self.playwright.chromium.connect_over_cdp(ws_url)
                    print("✅ Connected to Browserless successfully")
                    
                    # Get existing contexts from Browserless
                    contexts = self.browser.contexts
                    if contexts:
                        # Use existing context
                        context = contexts[0]
                        print("✅ Using existing Browserless context")
                    else:
                        # Create new context if none exists
                        context = self.browser.new_context(
                            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            viewport={'width': 1920, 'height': 1080},
                            java_script_enabled=True,
                        )
                        print("✅ Created new Browserless context")
                    
                    # Add script to hide webdriver property
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """)
                    
                    # Get or create page
                    pages = context.pages
                    if pages:
                        self.page = pages[0]
                    else:
                        self.page = context.new_page()
                    
                    print("✅ Browserless page ready")
                    return  # Skip local browser setup
                    
                except Exception as e:
                    print(f"⚠️  Browserless connection failed: {e}")
                    print("   Falling back to local browser...")
                    browserless_url = None  # Fall back to local
            
            if not browserless_url:
                # Launch local browser with stealth options
                browser_args = [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
                
                self.browser = self.playwright.chromium.launch(
                    headless=True,
                    args=browser_args
                )
                print("✅ Local browser launched")
                
                # Create context with stealth settings
                context = self.browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    java_script_enabled=True,
                )
                
                # Add script to hide webdriver property
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                # Create page
                self.page = context.new_page()
                print("✅ Playwright browser initialized successfully")
            
        except Exception as e:
            error_msg = f"Error setting up Playwright browser: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            raise Exception(f"{error_msg}. Make sure Playwright browsers are installed. Run: playwright install chromium")
    
    def close(self):
        """Close the browser"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                # For Browserless connections, try disconnect() if close() fails
                try:
                    self.browser.close()
                except:
                    try:
                        self.browser.disconnect()
                    except:
                        pass
            if self.playwright:
                self.playwright.stop()
        except:
            pass
    
    def extract_vehicles_from_search_url(self, search_url, limit=20, description=""):
        """Extract all vehicle data directly from search results page (MUCH FASTER)"""
        vehicles = []
        
        # Initialize browser if not already done
        if not self.page:
            try:
                print("Initializing Playwright browser...")
                self.setup_browser()
                if not self.page:
                    print("❌ Browser initialization failed - page is None")
                    return vehicles
            except Exception as e:
                print(f"❌ Error initializing browser: {e}")
                import traceback
                traceback.print_exc()
                return vehicles
        
        if not self.page:
            print("❌ No browser available - cannot scrape")
            return vehicles
        
        try:
            print(f"Navigating to Copart search results ({description})...")
            self.page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for page to load - Copart uses heavy JavaScript rendering
            print("Waiting for page to load...")
            time.sleep(10)  # Increased wait time for JavaScript to render
            
            # Wait for content to be ready
            try:
                self.page.wait_for_load_state('networkidle', timeout=30000)
            except:
                pass
            
            # Additional wait for dynamic content
            time.sleep(5)
            
            # Try to wait for any lot links to appear
            try:
                self.page.wait_for_selector('a[href*="/lot/"]', timeout=15000, state='attached')
                print("✅ Lot links detected on page")
            except:
                print("⚠️  No lot links found after waiting - page may require login or have no results")
            
            page_source = self.page.content()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract vehicles from search results table/rows
            # Copart search results are typically in table rows or div containers
            vehicle_rows = []
            
            # Method 1: Look for table rows with lot data
            table_rows = soup.find_all('tr')
            method1_count = 0
            for row in table_rows:
                row_text = row.get_text()
                # Check if row contains lot number pattern
                if re.search(r'Lot\s*#\s*:?\s*\d{8}', row_text, re.IGNORECASE) or re.search(r'1-\d{8}', row_text):
                    vehicle_rows.append(row)
                    method1_count += 1
            if method1_count > 0:
                print(f"    Method 1 found {method1_count} rows")
            
            # Method 2: Look for div containers with lot data
            if not vehicle_rows:
                lot_containers = soup.find_all(['div', 'section'], attrs={'data-lot-number': True})
                vehicle_rows.extend(lot_containers)
                if lot_containers:
                    print(f"    Method 2 found {len(lot_containers)} containers")
            
            # Method 3: Look for elements with lot links - use link itself (href contains all data)
            if not vehicle_rows:
                print(f"    Trying Method 3: Looking for lot links...")
                lot_links = soup.find_all('a', href=re.compile(r'/lot/\d+'))
                print(f"    Found {len(lot_links)} lot links in page")
                seen_lots = set()
                for link in lot_links:
                    # Extract lot number from href
                    href = link.get('href', '')
                    lot_match = re.search(r'/lot/(\d+)', href)
                    if lot_match:
                        lot_num = lot_match.group(1)
                        if lot_num not in seen_lots:  # Avoid duplicates
                            seen_lots.add(lot_num)
                            # Use the link itself - it has the href with lot, year, location data
                            vehicle_rows.append(link)
                print(f"    Method 3 added {len(vehicle_rows)} unique links to vehicle_rows")
            
            # Method 4: Extract directly from lot links - use link itself as row element
            if not vehicle_rows:
                lot_links = soup.find_all('a', href=re.compile(r'/lot/\d+'))
                seen_lots = set()
                for link in lot_links[:limit*2]:  # Get more links to account for duplicates
                    href = link.get('href', '')
                    lot_match = re.search(r'/lot/(\d+)', href)
                    if lot_match:
                        lot_num = lot_match.group(1)
                        if lot_num not in seen_lots:
                            seen_lots.add(lot_num)
                            # Use the link itself as the row element (it contains the href with all data)
                            vehicle_rows.append(link)
            
            print(f"  Found {len(vehicle_rows)} vehicle rows from {description}")
            
            # Extract data from each row
            for i, row in enumerate(vehicle_rows[:limit], 1):
                try:
                    # Debug: check what type of element we have
                    if i <= 3:  # Only debug first 3
                        if hasattr(row, 'name'):
                            print(f"    Row {i}: {row.name}, href: {row.get('href', 'N/A')[:50] if row.name == 'a' else 'N/A'}")
                    
                    vehicle = self._extract_vehicle_from_row(row, page_source)
                    if vehicle and vehicle.get("lot_number") != "N/A":
                        vehicles.append(vehicle)
                        if len(vehicles) >= limit:
                            break
                    elif vehicle:
                        if i <= 3:
                            print(f"    Row {i}: Extracted but lot_number is N/A")
                except Exception as e:
                    print(f"  Error extracting vehicle {i}: {str(e)}")
                    continue
            
            print(f"  Extracted {len(vehicles)} vehicles from {description}")
            return vehicles
            
        except Exception as e:
            print(f"Error extracting vehicles from {description}: {str(e)}")
            import traceback
            traceback.print_exc()
            return vehicles
    
    def _extract_vehicle_from_row(self, row_element, page_source):
        """Extract vehicle data from a search results row"""
        vehicle = {
            "lot_number": "N/A",
            "year": None,
            "make": "Toyota",
            "model": "Corolla",
            "damage": "N/A",
            "location": "N/A",
            "location_state": "N/A",
            "odometer": "N/A",
            "current_bid": "N/A",
            "auction_countdown": "N/A",
            "url": "N/A",
            "title": "N/A",
            "condition": "N/A",
            "sale_info": "N/A",
            "images": []  # List of image URLs
        }
        
        row_text = row_element.get_text()
        row_html = str(row_element)
        
        # Don't extract images from search results - we'll get them from individual lot pages for max quality
        vehicle["images"] = []
        
        # Extract Lot Number and other data from href (IMPROVED - href contains lot, year, location)
        # Check if row_element itself is a link
        href = None
        if row_element.name == 'a' and row_element.get('href'):
            href = row_element.get('href')
        else:
            # Otherwise, look for links in the row
            lot_links = row_element.find_all('a', href=re.compile(r'/lot/\d+'))
            if lot_links:
                href = lot_links[0].get('href', '')
        
        if href:
            # Extract lot number from href: /lot/97008115/...
            lot_match = re.search(r'/lot/(\d+)', href)
            if lot_match:
                lot_num = lot_match.group(1)
                vehicle["lot_number"] = lot_num
                vehicle["url"] = f"https://www.copart.com/lot/{lot_num}"
                
                # Extract year from href: ...-2017-toyota-...
                year_match = re.search(r'-(\d{4})-', href)
                if year_match:
                    try:
                        vehicle["year"] = int(year_match.group(1))
                    except:
                        pass
                
                # Extract location from href: ...-md-baltimore or ...-nj-...
                location_match = re.search(r'-(md|dc|nj|ny)-', href, re.IGNORECASE)
                if location_match:
                    state = location_match.group(1).upper()
                    vehicle["location_state"] = state
                    vehicle["location"] = state
                
                # Extract damage from href if present
                damage_keywords = ['front', 'rear', 'side', 'all-over', 'vandalism', 'hail', 'water', 'flood']
                for damage in damage_keywords:
                    if damage in href.lower():
                        if damage == 'front':
                            vehicle["damage"] = "Front End"
                        elif damage == 'rear':
                            vehicle["damage"] = "Rear End"
                        elif damage == 'side':
                            vehicle["damage"] = "Side"
                        else:
                            vehicle["damage"] = damage.title()
                        break
        
        # Fallback to text patterns if not found in links
        if vehicle["lot_number"] == "N/A":
            lot_match = re.search(r'Lot\s*#\s*:?\s*(\d{8})', row_text, re.IGNORECASE)
            if not lot_match:
                lot_match = re.search(r'(?:1-)?(\d{8})', row_text)
            if lot_match:
                lot_num = lot_match.group(1)  # Get just the 8 digits, no "1-" prefix
                vehicle["lot_number"] = lot_num
                vehicle["url"] = f"https://www.copart.com/lot/{lot_num}"
        
        # Extract Year from car name/description
        year_match = re.search(r'\b(201[7-9]|202[0-3])\b', row_text)
        if year_match:
            try:
                vehicle["year"] = int(year_match.group(1))
            except:
                pass
        
        # Extract Odometer (improved patterns)
        odometer_patterns = [
            r'Odometer[:\s]*(\d{1,3}[,\d]*)\s*(?:miles?|mi)?',
            r'(\d{1,3}[,\d]*)\s*(?:miles?|mi)\s*(?:on|odometer)',
            r'(\d{1,3}[,\d]*)\s*(?:k\s*miles?)',
            r'(\d{1,3}[,\d]*)\s*(?:miles?|mi)',
            r'Mileage[:\s]*(\d{1,3}[,\d]*)',
        ]
        for pattern in odometer_patterns:
            odometer_match = re.search(pattern, row_text, re.IGNORECASE)
            if odometer_match:
                odometer_value = odometer_match.group(1).replace(',', '').replace(' ', '').strip()
                # Handle "k miles" format (e.g., "50k miles" = 50000)
                if 'k' in odometer_match.group(0).lower():
                    try:
                        odometer_value = str(int(float(odometer_value) * 1000))
                    except:
                        pass
                if odometer_value and odometer_value.isdigit():
                    vehicle["odometer"] = odometer_value
                    break
        
        # Extract Condition
        condition_patterns = [
            r'Condition[:\s]+([A-Za-z\s]+)',
            r'Status[:\s]+([A-Za-z\s]+)',
        ]
        for pattern in condition_patterns:
            condition_match = re.search(pattern, row_text, re.IGNORECASE)
            if condition_match:
                condition_value = condition_match.group(1).strip()
                vehicle["condition"] = condition_value[:50]  # Limit length
                break
        
        # Extract Damage
        damage_keywords = ['Front End', 'Rear End', 'Side', 'All Over', 'Vandalism', 'Hail', 'Water/Flood']
        for damage in damage_keywords:
            if damage.lower() in row_text.lower():
                vehicle["damage"] = damage
                break
        
        # Extract Location (MD, DC, NJ, NY)
        location_patterns = [
            r'\b(MD|DC|NJ|NY|Maryland|District of Columbia|New Jersey|New York)\b',
        ]
        for pattern in location_patterns:
            location_match = re.search(pattern, row_text, re.IGNORECASE)
            if location_match:
                state_text = location_match.group(1).upper()
                if state_text in ['MD', 'MARYLAND']:
                    vehicle["location_state"] = 'MD'
                    vehicle["location"] = 'MD'
                elif state_text in ['DC', 'DISTRICT OF COLUMBIA']:
                    vehicle["location_state"] = 'DC'
                    vehicle["location"] = 'DC'
                elif state_text in ['NJ', 'NEW JERSEY']:
                    vehicle["location_state"] = 'NJ'
                    vehicle["location"] = 'NJ'
                elif state_text in ['NY', 'NEW YORK']:
                    vehicle["location_state"] = 'NY'
                    vehicle["location"] = 'NY'
                break
        
        # Extract Current Bid
        bid_patterns = [
            r'Bid[:\s]+\$?([\d,]+)',
            r'Current\s+Bid[:\s]+\$?([\d,]+)',
            r'\$([\d,]+)',
        ]
        for pattern in bid_patterns:
            bid_match = re.search(pattern, row_text, re.IGNORECASE)
            if bid_match:
                bid_value = bid_match.group(1).replace(',', '').strip()
                if bid_value and bid_value.isdigit():
                    vehicle["current_bid"] = f"${bid_value}"
                    break
        
        # Extract Auction Countdown
        countdown_patterns = [
            r'(\d+\s*(?:d|day|days?)\s+\d+\s*(?:h|hour|hours?)\s+\d+\s*(?:min|minute|minutes?))',
            r'(\d+\s*(?:h|hour|hours?)\s+\d+\s*(?:min|minute|minutes?))',
        ]
        for pattern in countdown_patterns:
            countdown_match = re.search(pattern, row_text, re.IGNORECASE)
            if countdown_match:
                vehicle["auction_countdown"] = countdown_match.group(1)
                break
        
        # Extract Sale Info
        sale_patterns = [
            r'Sale\s+(?:Date|Time)[:\s]+([^\n]+)',
            r'Auction[:\s]+([^\n]+)',
        ]
        for pattern in sale_patterns:
            sale_match = re.search(pattern, row_text, re.IGNORECASE)
            if sale_match:
                vehicle["sale_info"] = sale_match.group(1).strip()[:100]
                break
        
        # Extract Title (Salvage check)
        if 'salvage' in row_text.lower():
            vehicle["title"] = "Salvage"
        
        # Only return vehicle if we have at least a lot number
        if vehicle["lot_number"] != "N/A":
            return vehicle
        else:
            # Debug: check if we have a link but didn't extract lot number
            links = row_element.find_all('a', href=re.compile(r'/lot/\d+'))
            if links:
                print(f"  Warning: Found link but didn't extract lot number. Link: {links[0].get('href', '')[:50]}")
        
        return None
    
    def extract_vehicles_from_search_results(self, filter_by_location=False):
        """Extract all vehicle data directly from search results (MUCH FASTER - no individual page visits)
        
        Strategy: Split into two searches to bypass pagination:
        1. Search for MD/DC/NJ (20 cars) - extract all data from search page
        2. Search for NY (20 cars) - extract all data from search page
        3. Merge and filter results
        """
        all_vehicles = []
        
        # Initialize browser if not already done
        if not self.page:
            try:
                self.setup_browser()
            except Exception as e:
                print(f"Error initializing browser: {e}")
                return all_vehicles
        
        if not self.page:
            return all_vehicles
        
        try:
            # Search 1: MD, DC, NJ (20 cars)
            search_url_md_dc_nj = "https://www.copart.com/lotSearchResults?free=true&query=&qId=51ad8d38-cfcc-485f-8336-1d845c5583df-1769321379269&index=0&searchCriteria=%7B%22query%22:%5B%22*%22%5D,%22filter%22:%7B%22TITL%22:%5B%22title_group_code:TITLEGROUP_S%22%5D,%22LOC%22:%5B%22yard_name:%5C%22DC%20-%20WASHINGTON%20DC%5C%22%22,%22yard_name:%5C%22MD%20-%20BALTIMORE%5C%22%22,%22yard_name:%5C%22MD%20-%20BALTIMORE%20EAST%5C%22%22,%22yard_name:%5C%22NJ%20-%20GLASSBORO%20EAST%5C%22%22,%22yard_name:%5C%22NJ%20-%20SOMERVILLE%5C%22%22,%22yard_name:%5C%22NJ%20-%20TRENTON%5C%22%22%5D,%22MAKE%22:%5B%22lot_make_desc:%5C%22TOYOTA%5C%22%22%5D,%22MODL%22:%5B%22manufacturer_model_desc:%5C%22COROLLA%5C%22%22%5D,%22PRID%22:%5B%22damage_type_code:DAMAGECODE_FR%22,%22damage_type_code:DAMAGECODE_RR%22,%22damage_type_code:DAMAGECODE_SD%22%5D,%22YEAR%22:%5B%22lot_year:%5B2017%20TO%202023%5D%22%5D,%22FETI%22:%5B%22lot_condition_code:CERT-D%22%5D%7D,%22searchName%22:%22%22,%22watchListOnly%22:false,%22freeFormSearch%22:false%7D"
            
            print("  Starting search 1: MD/DC/NJ...")
            vehicles_1 = self.extract_vehicles_from_search_url(
                search_url_md_dc_nj, 
                limit=20, 
                description="MD/DC/NJ"
            )
            print(f"  Search 1 returned {len(vehicles_1)} vehicles")
            all_vehicles.extend(vehicles_1)
            
            # Search 2: NY (20 cars)
            search_url_ny = "https://www.copart.com/lotSearchResults?free=true&query=&qId=51ad8d38-cfcc-485f-8336-1d845c5583df-1769321379269&index=0&searchCriteria=%7B%22query%22:%5B%22*%22%5D,%22filter%22:%7B%22TITL%22:%5B%22title_group_code:TITLEGROUP_S%22%5D,%22LOC%22:%5B%22yard_name:%5C%22NY%20-%20ALBANY%5C%22%22,%22yard_name:%5C%22NY%20-%20BUFFALO%5C%22%22,%22yard_name:%5C%22NY%20-%20NEW%20YORK%5C%22%22,%22yard_name:%5C%22NY%20-%20ROCHESTER%5C%22%22,%22yard_name:%5C%22NY%20-%20SYRACUSE%5C%22%22%5D,%22MAKE%22:%5B%22lot_make_desc:%5C%22TOYOTA%5C%22%22%5D,%22MODL%22:%5B%22manufacturer_model_desc:%5C%22COROLLA%5C%22%22%5D,%22PRID%22:%5B%22damage_type_code:DAMAGECODE_FR%22,%22damage_type_code:DAMAGECODE_RR%22,%22damage_type_code:DAMAGECODE_SD%22%5D,%22YEAR%22:%5B%22lot_year:%5B2017%20TO%202023%5D%22%5D,%22FETI%22:%5B%22lot_condition_code:CERT-D%22%5D%7D,%22searchName%22:%22%22,%22watchListOnly%22:false,%22freeFormSearch%22:false%7D"
            
            print("  Starting search 2: NY...")
            vehicles_2 = self.extract_vehicles_from_search_url(
                search_url_ny, 
                limit=20, 
                description="NY"
            )
            print(f"  Search 2 returned {len(vehicles_2)} vehicles")
            all_vehicles.extend(vehicles_2)
            
            # Filter vehicles by location, title, and odometer
            filtered_vehicles = []
            for vehicle in all_vehicles:
                # Check location
                location_state = vehicle.get("location_state", "N/A")
                if location_state not in ['MD', 'DC', 'NJ', 'NY']:
                    continue
                
                # Check title (must be Salvage) - also check href for salvage keyword
                title = vehicle.get("title", "").upper()
                url = vehicle.get("url", "").upper()
                if "SALVAGE" not in title and "SALVAGE" not in url:
                    # Check if href contains salvage (most reliable)
                    continue
                
                # Filter by odometer (must be under 100,000 miles)
                odometer = vehicle.get('odometer', 'N/A')
                if odometer != 'N/A':
                    try:
                        # Remove commas and convert to int
                        odometer_value = int(str(odometer).replace(',', '').replace(' ', ''))
                        if odometer_value >= 100000:
                            continue  # Skip vehicles with 100,000+ miles
                    except (ValueError, AttributeError):
                        # If odometer can't be parsed, skip this vehicle
                        continue
                else:
                    # If odometer is N/A, skip this vehicle (we only want vehicles with known odometer)
                    continue
                
                filtered_vehicles.append(vehicle)
            
            print(f"\n✅ Total vehicles extracted: {len(all_vehicles)}")
            print(f"   - From MD/DC/NJ: {len(vehicles_1)}")
            print(f"   - From NY: {len(vehicles_2)}")
            print(f"   - After filtering: {len(filtered_vehicles)}")
            
            # Fetch high-quality images from individual lot pages for ALL vehicles
            print(f"\n📸 Fetching high-quality images from individual lot pages for {len(filtered_vehicles)} vehicles...")
            vehicles_with_images = []
            for i, vehicle in enumerate(filtered_vehicles, 1):
                lot_number = vehicle.get("lot_number", "N/A")
                if lot_number != "N/A":
                    try:
                        print(f"  [{i}/{len(filtered_vehicles)}] Fetching images for lot {lot_number}...")
                        lot_images = self._fetch_images_from_lot_page(lot_number)
                        if lot_images and len(lot_images) > 0:
                            # Ensure all images maintain maximum quality
                            high_quality_images = []
                            for img_url in lot_images:
                                # Clean URL to ensure maximum quality
                                clean_url = img_url
                                # Replace thumbnail/small/medium with full
                                clean_url = clean_url.replace('/thumb/', '/full/').replace('/small/', '/full/').replace('/medium/', '/full/')
                                # Remove any size/quality parameters
                                clean_url = re.sub(r'[?&](width|height|w|h|size|quality|scale|resize)=\d+', '', clean_url)
                                # Ensure it's using /full/ path for Copart images
                                if 'cs.copart.com' in clean_url and '/full/' not in clean_url:
                                    # Try to replace any size path with /full/
                                    clean_url = re.sub(r'/(thumb|small|medium|large)/', '/full/', clean_url)
                                high_quality_images.append(clean_url)
                            
                            vehicle["images"] = high_quality_images
                            print(f"      ✅ Found {len(high_quality_images)} high-quality images")
                        else:
                            # Fallback to default high-quality URLs
                            default_images = []
                            for img_num in range(1, 6):
                                default_images.append(f"https://cs.copart.com/v1/AUTH_svc.pdoc/00000/{lot_number}/full/{lot_number}_{img_num}.jpg")
                            vehicle["images"] = default_images
                            print(f"      ⚠️  Using default high-quality image URLs ({len(default_images)} images)")
                    except Exception as e:
                        print(f"      ⚠️  Error fetching images: {e}")
                        # Fallback to default high-quality URLs
                        default_images = []
                        for img_num in range(1, 6):
                            default_images.append(f"https://cs.copart.com/v1/AUTH_svc.pdoc/00000/{lot_number}/full/{lot_number}_{img_num}.jpg")
                        vehicle["images"] = default_images
                        print(f"      ✅ Using fallback high-quality URLs ({len(default_images)} images)")
                
                # Always add vehicle, even if no images found (will use defaults)
                vehicles_with_images.append(vehicle)
            
            print(f"\n✅ Image fetching complete: {len(vehicles_with_images)} vehicles with images")
            return vehicles_with_images
            
        except Exception as e:
            print(f"Error extracting vehicles: {str(e)}")
            import traceback
            traceback.print_exc()
            return filtered_vehicles
    
    def _fetch_images_from_lot_page(self, lot_number):
        """Fetch high-quality images from a specific lot page"""
        if not self.page:
            return []
        
        try:
            # Remove "1-" prefix if present
            if lot_number.startswith('1-'):
                lot_number = lot_number[2:]
            
            copart_url = f"https://www.copart.com/lot/{lot_number}"
            
            # Navigate to the lot page
            self.page.goto(copart_url, wait_until='networkidle', timeout=20000)
            time.sleep(2)  # Wait for images to load
            
            # Get page source
            page_source = self.page.content()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            images = []
            
            # Method 1: Look for high-quality image attributes
            img_tags = soup.find_all('img')
            for img in img_tags:
                # Prioritize high-quality attributes
                img_src = img.get('data-full') or img.get('data-original') or img.get('data-src') or img.get('src') or img.get('data-lazy-src')
                if img_src and ('vehicle' in img_src.lower() or 'lot' in img_src.lower() or 'copart' in img_src.lower() or 'cs.copart.com' in img_src.lower()):
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = 'https://www.copart.com' + img_src
                    # Replace thumbnail/small sizes with full size
                    img_src = img_src.replace('/thumb/', '/full/').replace('/small/', '/full/').replace('/medium/', '/full/')
                    # Remove size parameters
                    img_src = re.sub(r'[?&](width|height|w|h|size|quality)=\d+', '', img_src)
                    if img_src.startswith('http'):
                        images.append(img_src)
            
            # Method 2: Look for Copart's standard image URLs in page source - get ALL images (1-20)
            # Pattern: https://cs.copart.com/v1/AUTH_svc.pdoc/00000/{lot}/full/{lot}_{num}.jpg
            # Try to find all image numbers (1-20) for maximum coverage
            for img_num in range(1, 21):
                img_url = f"https://cs.copart.com/v1/AUTH_svc.pdoc/00000/{lot_number}/full/{lot_number}_{img_num}.jpg"
                # Check if this URL exists in page source
                if img_url in page_source or f'{lot_number}_{img_num}' in page_source:
                    if img_url not in images:
                        images.append(img_url)
            
            # Also search for any Copart image URLs in the page
            copart_image_pattern = rf'https://cs\.copart\.com/v1/AUTH_svc\.pdoc/\d+/{lot_number}/(?:full|large)/{lot_number}_\d+\.jpg'
            image_matches = re.findall(copart_image_pattern, page_source, re.IGNORECASE)
            for img_url in image_matches:
                # Ensure /full/ path
                img_url = img_url.replace('/large/', '/full/')
                if img_url not in images:
                    images.append(img_url)
            
            # Method 3: Try to find image gallery or carousel - get ALL images
            # Look for data attributes that might contain image URLs
            data_attrs = soup.find_all(attrs={'data-image': True})
            for elem in data_attrs:
                img_src = elem.get('data-image')
                if img_src:
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = 'https://www.copart.com' + img_src
                    # Replace all size paths with /full/ for maximum quality
                    img_src = img_src.replace('/thumb/', '/full/').replace('/small/', '/full/').replace('/medium/', '/full/').replace('/large/', '/full/')
                    # Remove ALL quality/size parameters
                    img_src = re.sub(r'[?&](width|height|w|h|size|quality|scale|resize|maxwidth|maxheight)=\d+', '', img_src)
                    if img_src.startswith('http') and img_src not in images:
                        images.append(img_src)
            
            # Method 4: Look for image arrays in JavaScript/data attributes
            # Some pages have image arrays in data attributes
            for elem in soup.find_all(attrs={'data-images': True}):
                try:
                    import json
                    images_json = elem.get('data-images')
                    if images_json:
                        img_list = json.loads(images_json)
                        for img_url in img_list:
                            if isinstance(img_url, str):
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                elif img_url.startswith('/'):
                                    img_url = 'https://www.copart.com' + img_url
                                img_url = img_url.replace('/thumb/', '/full/').replace('/small/', '/full/').replace('/medium/', '/full/').replace('/large/', '/full/')
                                img_url = re.sub(r'[?&](width|height|w|h|size|quality|scale|resize)=\d+', '', img_url)
                                if img_url.startswith('http') and img_url not in images:
                                    images.append(img_url)
                except:
                    pass
            
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for img in images:
                # Normalize URL to avoid duplicates
                normalized = img.split('?')[0]  # Remove query params for comparison
                if normalized not in seen:
                    seen.add(normalized)
                    unique_images.append(img)
            
            # Ensure all images maintain maximum quality - clean them again
            final_images = []
            for img_url in unique_images:
                # Final quality check - ensure /full/ path and no size params
                clean_url = img_url
                clean_url = clean_url.replace('/thumb/', '/full/').replace('/small/', '/full/').replace('/medium/', '/full/').replace('/large/', '/full/')
                clean_url = re.sub(r'[?&](width|height|w|h|size|quality|scale|resize|maxwidth|maxheight)=\d+', '', clean_url)
                # Ensure Copart images use /full/ path
                if 'cs.copart.com' in clean_url:
                    clean_url = re.sub(r'/(thumb|small|medium|large)/', '/full/', clean_url)
                final_images.append(clean_url)
            
            # If we found images, return them (all at maximum quality)
            if final_images:
                return final_images
            
            # Fallback: Try Copart's standard high-quality image URLs (try more images: 1-10)
            default_images = []
            for img_num in range(1, 11):
                default_images.append(f"https://cs.copart.com/v1/AUTH_svc.pdoc/00000/{lot_number}/full/{lot_number}_{img_num}.jpg")
            return default_images
            
        except Exception as e:
            # Return default high-quality URLs as fallback
            default_images = []
            for img_num in range(1, 6):
                default_images.append(f"https://cs.copart.com/v1/AUTH_svc.pdoc/00000/{lot_number}/full/{lot_number}_{img_num}.jpg")
            return default_images
    
    def scrape_copart_lot(self, lot_number):
        """Scrape a single Copart lot page"""
        if not self.page:
            return None
        
        try:
            # Remove "1-" prefix if present
            if lot_number.startswith('1-'):
                lot_number = lot_number[2:]
            
            copart_url = f"https://www.copart.com/lot/{lot_number}"
            print(f"Scraping Copart lot: {lot_number}")
            
            self.page.goto(copart_url, wait_until='networkidle', timeout=30000)
            time.sleep(2)
            
            try:
                self.page.wait_for_selector('body', timeout=10000)
            except:
                pass
            
            time.sleep(1)
            
            page_source = self.page.content()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Optimized body text extraction
            try:
                body_text = self.page.evaluate("() => document.body.innerText || document.body.textContent || ''")
            except:
                try:
                    body_text = self.page.locator('body').inner_text()
                except:
                    body_text = page_source
            
            # Initialize vehicle data
            vehicle = {
                "lot_number": lot_number,
                "year": None,
                "make": "Toyota",
                "model": "Corolla",
                "damage": "N/A",
                "location": "N/A",
                "odometer": "N/A",
                "current_bid": "N/A",
                "auction_countdown": "N/A",
                "url": copart_url,
                "images": []
            }
            
            # Extract images from the lot page - prioritize high quality
            img_tags = soup.find_all('img')
            for img in img_tags:
                # Try multiple attributes in order of preference (high quality first)
                img_src = img.get('data-full') or img.get('data-original') or img.get('data-src') or img.get('src') or img.get('data-lazy-src')
                if img_src and ('vehicle' in img_src.lower() or 'lot' in img_src.lower() or 'copart' in img_src.lower()):
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = 'https://www.copart.com' + img_src
                    # Replace thumbnail/small sizes with full size
                    img_src = img_src.replace('/thumb/', '/full/').replace('/small/', '/full/').replace('/medium/', '/full/')
                    # Remove size parameters
                    img_src = re.sub(r'[?&](width|height|w|h|size|quality)=\d+', '', img_src)
                    if img_src.startswith('http'):
                        vehicle["images"].append(img_src)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for img in vehicle["images"]:
                if img not in seen:
                    seen.add(img)
                    unique_images.append(img)
            vehicle["images"] = unique_images
            
            # If no images found, use default high-quality Copart image URLs
            if not vehicle["images"]:
                # Try multiple image numbers (1-5) for best coverage
                default_images = []
                for img_num in range(1, 6):
                    default_images.append(f"https://cs.copart.com/v1/AUTH_svc.pdoc/00000/{lot_number}/full/{lot_number}_{img_num}.jpg")
                vehicle["images"] = default_images
            
            # Extract Year - Look for "Year" tag on the page
            year = None
            
            # Method 1: Look for "Year" tag/label followed by year value
            # Find elements containing "Year" text
            year_elements = soup.find_all(string=re.compile(r'^Year$|^Year:', re.IGNORECASE))
            for elem in year_elements:
                parent = elem.find_parent()
                if parent:
                    parent_text = parent.get_text()
                    # Pattern: "Year: 2020" or "Year 2020"
                    year_match = re.search(r'Year[:\s]+(\d{4})', parent_text, re.IGNORECASE)
                    if year_match:
                        year_val = year_match.group(1)
                        try:
                            year_val_int = int(year_val)
                            if 2017 <= year_val_int <= 2023:
                                year = year_val_int
                                break
                        except:
                            pass
                if year:
                    break
            
            # Method 2: Look for label with "Year" and get value from next element
            if not year:
                year_labels = soup.find_all('label', string=re.compile(r'Year', re.IGNORECASE))
                for label in year_labels:
                    # Check next sibling for value
                    next_sibling = label.find_next_sibling()
                    if next_sibling:
                        sibling_text = next_sibling.get_text().strip()
                        year_match = re.search(r'(\d{4})', sibling_text)
                        if year_match:
                            try:
                                year_val = int(year_match.group(1))
                                if 2017 <= year_val <= 2023:
                                    year = year_val
                                    break
                            except:
                                pass
                    # Check parent for value
                    parent = label.find_parent()
                    if parent:
                        parent_text = parent.get_text()
                        year_match = re.search(r'Year[:\s]+(\d{4})', parent_text, re.IGNORECASE)
                        if year_match:
                            try:
                                year_val = int(year_match.group(1))
                                if 2017 <= year_val <= 2023:
                                    year = year_val
                                    break
                            except:
                                pass
                if year:
                    pass
            
            # Method 3: Look for year in title tag (e.g., "2022 TOYOTA COROLLA SE")
            if not year:
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    # Pattern: "YEAR TOYOTA COROLLA" - year comes BEFORE TOYOTA
                    title_year_pattern = r'(\d{4})\s+TOYOTA\s+COROLLA'
                    year_match = re.search(title_year_pattern, title_text, re.IGNORECASE)
                    if year_match:
                        year_val = year_match.group(1)
                        try:
                            year_val_int = int(year_val)
                            if 2017 <= year_val_int <= 2023:
                                year = year_val_int
                        except:
                            pass
            
            # Method 2: Look for year in headings (h1, h2, h3, h4) with Toyota Corolla
            if not year:
                heading_elements = soup.find_all(['h1', 'h2', 'h3', 'h4'])
                for elem in heading_elements:
                    elem_text = elem.get_text()
                    # Look for pattern: "YEAR TOYOTA COROLLA" - year comes BEFORE TOYOTA
                    if 'TOYOTA' in elem_text.upper() or 'COROLLA' in elem_text.upper():
                        title_year_pattern = r'(\d{4})\s+TOYOTA\s+COROLLA'
                        year_match = re.search(title_year_pattern, elem_text, re.IGNORECASE)
                        if year_match:
                            year_val = year_match.group(1)
                            try:
                                year_val_int = int(year_val)
                                if 2017 <= year_val_int <= 2023:
                                    year = year_val_int
                                    break
                            except:
                                pass
                if year:
                    pass
            
            # Method 3: Look for year in body text near "Toyota Corolla"
            if not year:
                # Pattern: "YEAR TOYOTA COROLLA" - year comes BEFORE TOYOTA
                toyota_year_pattern = r'(\d{4})\s+TOYOTA\s+COROLLA'
                toyota_match = re.search(toyota_year_pattern, body_text, re.IGNORECASE)
                if toyota_match:
                    year_val = toyota_match.group(1)
                    try:
                        year_val_int = int(year_val)
                        if 2017 <= year_val_int <= 2023:
                            year = year_val_int
                    except:
                        pass
            
            # Method 4: Look for "Year" keyword followed by year
            if not year:
                year_keywords = ['Year', 'Model Year', 'Vehicle Year', 'Lot Year']
                for keyword in year_keywords:
                    year_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                    for elem in year_elements:
                        parent = elem.find_parent()
                        if parent:
                            parent_text = parent.get_text()
                            year_match = re.search(rf'{keyword}[:\s]+(\d{{4}})', parent_text, re.IGNORECASE)
                            if year_match:
                                try:
                                    year_val = int(year_match.group(1))
                                    if 2017 <= year_val <= 2023:
                                        year = year_val
                                        break
                                except:
                                    pass
                        if year:
                            break
                    if year:
                        break
            
            # Method 5: Look for year in page source (2017-2023)
            if not year:
                year_pattern = r'\b(201[7-9]|202[0-3])\b'
                year_matches = re.findall(year_pattern, page_source)
                if year_matches:
                    for year_str in year_matches:
                        try:
                            year_val = int(year_str)
                            if 2017 <= year_val <= 2023:
                                year = year_val
                                break
                        except:
                            pass
            
            vehicle["year"] = year
            
            # Extract Location - EXACT text from Copart page
            location = "N/A"
            location_text = "N/A"
            
            # Method 1: Look for location keywords - extract FULL location text
            location_keywords = ['Location', 'yard', 'facility', 'site', 'pickup']
            for keyword in location_keywords:
                location_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for elem in location_elements:
                    parent = elem.find_parent()
                    if parent:
                        parent_text = parent.get_text()
                        # Extract full location text after keyword
                        location_match = re.search(rf'{keyword}[:\s]+([^\n\r<]+?)(?:\n|$|</)', parent_text, re.IGNORECASE | re.DOTALL)
                        if location_match:
                            loc_text = location_match.group(1).strip()
                            loc_text = re.sub(r'\s+', ' ', loc_text)
                            loc_text = loc_text.split('\n')[0].strip()
                            # Remove common suffixes
                            loc_text = re.sub(r',\s*(?:USA|United States|US).*', '', loc_text, flags=re.IGNORECASE)
                            loc_text = loc_text.strip()
                            
                            # Verify it contains one of our states and keep FULL text
                            if re.search(r'\b(MD|Maryland)\b', loc_text, re.IGNORECASE):
                                location_text = loc_text  # Keep full text like "Baltimore, MD"
                                location = 'MD'
                                break
                            elif re.search(r'\b(NJ|New Jersey)\b', loc_text, re.IGNORECASE):
                                location_text = loc_text
                                location = 'NJ'
                                break
                            elif re.search(r'\b(DC|District of Columbia|Washington DC)\b', loc_text, re.IGNORECASE):
                                location_text = loc_text
                                location = 'DC'
                                break
                            elif re.search(r'\b(NY|New York)\b', loc_text, re.IGNORECASE):
                                location_text = loc_text
                                location = 'NY'
                                break
                    if location != "N/A":
                        break
                if location != "N/A":
                    break
            
            # Method 2: Search for city-state patterns (common cities)
            if location == "N/A":
                # Common cities in our target states
                md_cities = ['Baltimore', 'Annapolis', 'Frederick', 'Rockville', 'Gaithersburg', 'Columbia', 'Germantown', 'Waldorf', 'Laurel', 'Bethesda', 'Silver Spring', 'Wheaton']
                nj_cities = ['Newark', 'Jersey City', 'Paterson', 'Elizabeth', 'Edison', 'Woodbridge', 'Lakewood', 'Toms River', 'Hamilton', 'Trenton', 'Clifton', 'Camden']
                dc_cities = ['Washington', 'District']
                ny_cities = ['New York', 'Albany', 'Buffalo', 'Rochester', 'Syracuse', 'Yonkers', 'Utica', 'White Plains', 'Hempstead', 'Troy', 'Binghamton', 'Freeport']
                
                # Try MD cities first
                for city in md_cities:
                    pattern = rf'{city}[,\s]+(MD|Maryland)'
                    match = re.search(pattern, body_text if body_text else page_source, re.IGNORECASE)
                    if match:
                        location_text = f"{city}, MD"
                        location = 'MD'
                        break
                
                # Try NJ cities
                if location == "N/A":
                    for city in nj_cities:
                        pattern = rf'{city}[,\s]+(NJ|New Jersey)'
                        match = re.search(pattern, body_text if body_text else page_source, re.IGNORECASE)
                        if match:
                            location_text = f"{city}, NJ"
                            location = 'NJ'
                            break
                
                # Try DC
                if location == "N/A":
                    for city in dc_cities:
                        pattern = rf'{city}[,\s]*(DC|District of Columbia)'
                        match = re.search(pattern, body_text if body_text else page_source, re.IGNORECASE)
                        if match:
                            location_text = f"{city}, DC"
                            location = 'DC'
                            break
                
                # Try NY cities
                if location == "N/A":
                    for city in ny_cities:
                        pattern = rf'{city}[,\s]+(NY|New York)'
                        match = re.search(pattern, body_text if body_text else page_source, re.IGNORECASE)
                        if match:
                            location_text = f"{city}, NY"
                            location = 'NY'
                            break
            
            # Method 2b: Generic city-state pattern
            if location == "N/A":
                city_state_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)'
                match = re.search(city_state_pattern, body_text if body_text else page_source)
                if match:
                    city = match.group(1).strip()
                    state = match.group(2).strip()
                    # Normalize state abbreviation
                    if state.upper() in ['MD', 'MARYLAND']:
                        location_text = f"{city}, MD"
                        location = 'MD'
                    elif state.upper() in ['NJ', 'NEW JERSEY']:
                        location_text = f"{city}, NJ"
                        location = 'NJ'
                    elif state.upper() in ['DC', 'DISTRICT OF COLUMBIA']:
                        location_text = f"{city}, DC"
                        location = 'DC'
                    elif state.upper() in ['NY', 'NEW YORK']:
                        location_text = f"{city}, NY"
                        location = 'NY'
            
            # Method 3: Fallback - just state
            if location == "N/A":
                if re.search(r'\b(MD|Maryland)\b', page_source, re.IGNORECASE):
                    location = 'MD'
                    location_text = 'MD'
                elif re.search(r'\b(NJ|New Jersey)\b', page_source, re.IGNORECASE):
                    location = 'NJ'
                    location_text = 'NJ'
                elif re.search(r'\b(DC|District of Columbia|Washington DC)\b', page_source, re.IGNORECASE):
                    location = 'DC'
                    location_text = 'DC'
                elif re.search(r'\b(NY|New York)\b', page_source, re.IGNORECASE):
                    location = 'NY'
                    location_text = 'NY'
            
            vehicle["location"] = location_text
            vehicle["location_state"] = location
            
            # Extract Location/Lane field - ADDITIONAL CHECK
            # This field appears on individual Copart lot pages
            # This is a separate field from Location on Copart pages
            location_lane_state = "N/A"
            location_lane_keywords = ['Location / Lane', 'Location/Lane', 'Lane', 'Location Lane']
            for keyword in location_lane_keywords:
                lane_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for elem in lane_elements:
                    parent = elem.find_parent()
                    if parent:
                        parent_text = parent.get_text()
                        # Extract text after Location/Lane keyword
                        lane_match = re.search(rf'{re.escape(keyword)}[:\s]+([^\n\r<]+?)(?:\n|$|</)', parent_text, re.IGNORECASE | re.DOTALL)
                        if lane_match:
                            lane_text = lane_match.group(1).strip()
                            lane_text = re.sub(r'\s+', ' ', lane_text)
                            lane_text = lane_text.split('\n')[0].strip()
                            
                            # Check for our states in Location/Lane
                            if re.search(r'\b(MD|Maryland)\b', lane_text, re.IGNORECASE):
                                location_lane_state = 'MD'
                                break
                            elif re.search(r'\b(NJ|New Jersey)\b', lane_text, re.IGNORECASE):
                                location_lane_state = 'NJ'
                                break
                            elif re.search(r'\b(DC|District of Columbia|Washington DC)\b', lane_text, re.IGNORECASE):
                                location_lane_state = 'DC'
                                break
                            elif re.search(r'\b(NY|New York)\b', lane_text, re.IGNORECASE):
                                location_lane_state = 'NY'
                                break
                    if location_lane_state != "N/A":
                        break
                if location_lane_state != "N/A":
                    break
            
            # Also search in page source for Location/Lane patterns
            if location_lane_state == "N/A":
                location_lane_patterns = [
                    r'(?:Location\s*/\s*Lane|Location/Lane)[:\s]*[^<\n]{0,50}?\b(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)\b',
                    r'Lane[:\s]+[^<\n]{0,50}?\b(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)\b',
                ]
                for pattern in location_lane_patterns:
                    match = re.search(pattern, page_source, re.IGNORECASE)
                    if match:
                        state_text = match.group(1).strip()
                        if state_text.upper() in ['MD', 'MARYLAND']:
                            location_lane_state = 'MD'
                            break
                        elif state_text.upper() in ['NJ', 'NEW JERSEY']:
                            location_lane_state = 'NJ'
                            break
                        elif state_text.upper() in ['DC', 'DISTRICT OF COLUMBIA']:
                            location_lane_state = 'DC'
                            break
                        elif state_text.upper() in ['NY', 'NEW YORK']:
                            location_lane_state = 'NY'
                            break
                    if location_lane_state != "N/A":
                        break
            
            # Extract Sale Document/Location - CRITICAL CHECK
            # This field on Copart shows where the sale document is located
            sale_doc_state = "N/A"
            
            # Method 1: Search for Sale Doc/Document keywords in HTML elements
            sale_doc_keywords = [
                'Sale doc', 'Sale document', 'Sale location', 'Document location', 
                'Sale yard', 'Sale Doc', 'Sale Document', 'saleDoc', 'saleDocLocation',
                'Document', 'Doc Location', 'Sale Site'
            ]
            for keyword in sale_doc_keywords:
                # Search in all text elements
                sale_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for elem in sale_elements:
                    parent = elem.find_parent()
                    if parent:
                        parent_text = parent.get_text()
                        # Extract text after keyword (more flexible pattern)
                        sale_match = re.search(rf'{re.escape(keyword)}[:\s]*([^\n\r<]+?)(?:\n|$|</|br)', parent_text, re.IGNORECASE | re.DOTALL)
                        if sale_match:
                            sale_text = sale_match.group(1).strip()
                            sale_text = re.sub(r'\s+', ' ', sale_text)
                            sale_text = sale_text.split('\n')[0].strip()
                            
                            # Check for our states in sale doc
                            if re.search(r'\b(MD|Maryland)\b', sale_text, re.IGNORECASE):
                                sale_doc_state = 'MD'
                                break
                            elif re.search(r'\b(NJ|New Jersey)\b', sale_text, re.IGNORECASE):
                                sale_doc_state = 'NJ'
                                break
                            elif re.search(r'\b(DC|District of Columbia|Washington DC)\b', sale_text, re.IGNORECASE):
                                sale_doc_state = 'DC'
                                break
                            elif re.search(r'\b(NY|New York)\b', sale_text, re.IGNORECASE):
                                sale_doc_state = 'NY'
                                break
                    if sale_doc_state != "N/A":
                        break
                if sale_doc_state != "N/A":
                    break
            
            # Method 2: Search in page source with multiple patterns (more specific)
            if sale_doc_state == "N/A":
                sale_doc_patterns = [
                    # Look for "Sale doc" or "Sale document" followed by state (within 50 chars)
                    r'(?:Sale\s+doc[ument]*|saleDoc)[:\s]*[^<\n]{0,50}?\b(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)\b',
                    # Look for "Sale location" followed by state
                    r'Sale\s+location[:\s]*[^<\n]{0,50}?\b(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)\b',
                    # Look for "Document location" followed by state
                    r'Document\s+location[:\s]*[^<\n]{0,50}?\b(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)\b',
                    # Look in data attributes
                    r'data-sale-doc[^=]*=[^>]*?\b(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)\b',
                    # Look in JSON-like structures
                    r'["\']saleDoc["\'][^}]*?["\'](MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)["\']',
                ]
                for pattern in sale_doc_patterns:
                    match = re.search(pattern, page_source, re.IGNORECASE)
                    if match:
                        state_text = match.group(1).strip()
                        # Verify it's a valid state code (not part of another word)
                        if state_text.upper() in ['MD', 'MARYLAND']:
                            sale_doc_state = 'MD'
                            break
                        elif state_text.upper() in ['NJ', 'NEW JERSEY']:
                            sale_doc_state = 'NJ'
                            break
                        elif state_text.upper() in ['DC', 'DISTRICT OF COLUMBIA']:
                            sale_doc_state = 'DC'
                            break
                        elif state_text.upper() in ['NY', 'NEW YORK']:
                            sale_doc_state = 'NY'
                            break
                    if sale_doc_state != "N/A":
                        break
            
            # Method 3: Search in data attributes and JSON data
            if sale_doc_state == "N/A":
                # Look for JSON data in script tags
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string:
                        # Look for state codes near "sale" or "doc" keywords
                        json_match = re.search(r'(?:sale|doc|location).*?(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)', script.string, re.IGNORECASE)
                        if json_match:
                            state_text = json_match.group(1).strip()
                            if state_text.upper() in ['MD', 'MARYLAND']:
                                sale_doc_state = 'MD'
                                break
                            elif state_text.upper() in ['NJ', 'NEW JERSEY']:
                                sale_doc_state = 'NJ'
                                break
                            elif state_text.upper() in ['DC', 'DISTRICT OF COLUMBIA']:
                                sale_doc_state = 'DC'
                                break
                            elif state_text.upper() in ['NY', 'NEW YORK']:
                                sale_doc_state = 'NY'
                                break
                if sale_doc_state != "N/A":
                    pass  # Found it
            
            # Extract Damage
            damage_keywords = ['primary damage', 'damage type', 'damage']
            if body_text:
                for keyword in damage_keywords:
                    damage_match = re.search(rf'{keyword}[:\s]+([A-Za-z\s/]+)', body_text, re.IGNORECASE)
                    if damage_match:
                        damage_value = damage_match.group(1).strip()
                        damage_value = re.sub(r'\s+', ' ', damage_value)
                        damage_value = re.sub(r'\s*(estimated retail value|secondary damage).*', '', damage_value, flags=re.IGNORECASE)
                        damage_value = damage_value.strip()
                        if len(damage_value) > 2:
                            vehicle["damage"] = damage_value
                            break
            
            # Extract Odometer - Multiple methods for better extraction
            odometer = "N/A"
            
            # Method 1: Look for "Odometer" keyword
            odometer_keywords = ['Odometer', 'Mileage', 'Miles', 'Odometer Reading']
            for keyword in odometer_keywords:
                odometer_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for elem in odometer_elements:
                    parent = elem.find_parent()
                    if parent:
                        parent_text = parent.get_text()
                        # Pattern: "Odometer: 123,456 miles" or "Mileage: 123456"
                        odometer_match = re.search(rf'{keyword}[:\s]+(\d{{1,3}}[,\d]*)\s*(?:miles?|mi|km)?', parent_text, re.IGNORECASE)
                        if odometer_match:
                            odometer_value = odometer_match.group(1).replace(',', '').strip()
                            if odometer_value and odometer_value.isdigit():
                                odometer = odometer_value
                                break
                    if odometer != "N/A":
                        break
                if odometer != "N/A":
                    break
            
            # Method 2: Look for odometer patterns in page source
            if odometer == "N/A":
                odometer_patterns = [
                    r'odometer[:\s]+(\d{1,3}[,\d]*)\s*(?:miles?|mi)',
                    r'(\d{1,3}[,\d]*)\s*(?:miles?|mi)\s*odometer',
                    r'mileage[:\s]+(\d{1,3}[,\d]*)\s*(?:miles?|mi)',
                    r'(\d{1,3}[,\d]*)\s*(?:miles?|mi)\s*mileage',
                ]
                for pattern in odometer_patterns:
                    odometer_match = re.search(pattern, page_source, re.IGNORECASE)
                    if odometer_match:
                        odometer_value = odometer_match.group(1).replace(',', '').strip()
                        if odometer_value and odometer_value.isdigit():
                            odometer = odometer_value
                            break
            
            # Method 3: Look for mileage in body text
            if odometer == "N/A" and body_text:
                mileage_patterns = [
                    r'(\d{1,3}[,\d]*)\s*(?:miles?|mi)\s*(?:on|odometer|mileage)',
                    r'(?:on|odometer|mileage)[:\s]+(\d{1,3}[,\d]*)\s*(?:miles?|mi)',
                ]
                for pattern in mileage_patterns:
                    mileage_match = re.search(pattern, body_text, re.IGNORECASE)
                    if mileage_match:
                        mileage_value = mileage_match.group(1).replace(',', '').strip()
                        if mileage_value and mileage_value.isdigit():
                            # Validate reasonable mileage (0 to 200,000 miles)
                            mileage_int = int(mileage_value)
                            if 0 <= mileage_int <= 200000:
                                odometer = mileage_value
                                break
            
            vehicle["odometer"] = odometer
            
            # Color extraction removed (not needed)
            
            # Extract Current Bid
            bid_patterns = [
                r'current bid[:\s]+\$?([\d,]+)',
                r'bid[:\s]+\$?([\d,]+)',
            ]
            if body_text:
                for pattern in bid_patterns:
                    bid_match = re.search(pattern, body_text, re.IGNORECASE)
                    if bid_match:
                        bid_value = bid_match.group(1).replace(',', '').strip()
                        if bid_value and bid_value != '0':
                            vehicle["current_bid"] = f"${bid_value}"
                            break
            
            # Extract Auction Countdown
            countdown_patterns = [
                r'(\d+\s*(?:d|day|days)\s+\d+\s*(?:h|hour|hours)\s+\d+\s*(?:min|minute|minutes?))\s*(?:left|remaining)?',
                r'(\d{1,2}:\d{2}:\d{2})\s*(?:left|remaining)',
            ]
            if body_text:
                for pattern in countdown_patterns:
                    countdown_match = re.search(pattern, body_text, re.IGNORECASE)
                    if countdown_match:
                        countdown_value = countdown_match.group(1).strip()
                        vehicle["auction_countdown"] = countdown_value
                        break
            
            # Extract Title - MUST contain "Salvage"
            title = "N/A"
            if "salvage" in page_source.lower() or "salvage" in body_text.lower():
                title_patterns = [
                    r'title[:\s]+(salvage)',
                    r'title\s+type[:\s]+(salvage)',
                    r'(salvage)\s+title',
                ]
                for pattern in title_patterns:
                    title_match = re.search(pattern, page_source, re.IGNORECASE)
                    if title_match:
                        title = "Salvage"
                        break
            
            vehicle["title"] = title
            
            # STRICT FILTERING - VERIFY FROM PAGE SOURCE AND SALE DOC
            # 1. Check location (must be MD, DC, NJ, or NY) - FINAL VERIFICATION
            location_state = vehicle.get("location_state", "N/A")
            
            # CRITICAL: Check Sale Document field - MUST include MD, DC, NJ, or NY
            # This is the PRIMARY check - Sale doc location is the most reliable
            if sale_doc_state != "N/A":
                print(f"  ✓ Sale doc found: {sale_doc_state}")
                if sale_doc_state not in ['MD', 'DC', 'NJ', 'NY']:
                    print(f"  ❌ FILTERED OUT: Sale doc shows '{sale_doc_state}' which is NOT MD/DC/NJ/NY")
                    return None
                # Sale doc is the authoritative source - use it
                location_state = sale_doc_state
                vehicle["location_state"] = sale_doc_state
                # Update location text if needed
                if vehicle.get("location") == "N/A" or vehicle.get("location") not in ['MD', 'DC', 'NJ', 'NY']:
                    vehicle["location"] = sale_doc_state
                # If location_state was different, log it but use Sale doc
                if vehicle.get("location_state", "N/A") != sale_doc_state:
                    print(f"  ⚠️  Note: Location field showed different state, but Sale doc is authoritative")
            else:
                # If sale doc not found, check Location/Lane field
                if location_lane_state != "N/A":
                    print(f"  ✓ Location/Lane found: {location_lane_state}")
                    if location_lane_state not in ['MD', 'DC', 'NJ', 'NY']:
                        print(f"  ❌ FILTERED OUT: Location/Lane shows '{location_lane_state}' which is NOT MD/DC/NJ/NY")
                        return None
                    # Use Location/Lane as location state
                    location_state = location_lane_state
                    vehicle["location_state"] = location_lane_state
                    if vehicle.get("location") == "N/A":
                        vehicle["location"] = location_lane_state
                else:
                    # If neither Sale doc nor Location/Lane found, verify location field
                    print(f"  ⚠️  Sale doc and Location/Lane not found - verifying location only")
                    if location_state not in ['MD', 'DC', 'NJ', 'NY']:
                        print(f"  ❌ FILTERED OUT: Location '{location_state}' is NOT MD/DC/NJ/NY")
                        return None
            
            # Double-check location from page source
            if location_state not in ['MD', 'DC', 'NJ', 'NY']:
                # Final check: search page one more time
                final_check = "N/A"
                if re.search(r'\b(MD|Maryland)\b', page_source, re.IGNORECASE):
                    # Make sure it's not part of another word
                    md_context = re.search(r'[^A-Za-z](MD|Maryland)[^A-Za-z]', page_source, re.IGNORECASE)
                    if md_context:
                        final_check = 'MD'
                elif re.search(r'\b(NJ|New Jersey)\b', page_source, re.IGNORECASE):
                    nj_context = re.search(r'[^A-Za-z](NJ|New Jersey)[^A-Za-z]', page_source, re.IGNORECASE)
                    if nj_context:
                        final_check = 'NJ'
                elif re.search(r'\b(DC|District of Columbia|Washington DC)\b', page_source, re.IGNORECASE):
                    final_check = 'DC'
                elif re.search(r'\b(NY|New York)\b', page_source, re.IGNORECASE):
                    ny_context = re.search(r'[^A-Za-z](NY|New York)[^A-Za-z]', page_source, re.IGNORECASE)
                    if ny_context:
                        final_check = 'NY'
                
                if final_check in ['MD', 'DC', 'NJ', 'NY']:
                    vehicle["location_state"] = final_check
                    if vehicle.get("location") == "N/A" or vehicle.get("location") == location_state:
                        vehicle["location"] = final_check
                    location_state = final_check
                else:
                    print(f"  ❌ FILTERED OUT: Location '{location_state}' is NOT MD/DC/NJ/NY (verified from Copart page)")
                    return None
            
            # Final verification - location_state MUST be one of our allowed states
            if location_state not in ['MD', 'DC', 'NJ', 'NY']:
                print(f"  ❌ FILTERED OUT: Final location check failed - '{location_state}'")
                return None
            
            # 2. Check title (must contain "Salvage")
            if "SALVAGE" not in vehicle.get("title", "").upper():
                print(f"  ❌ Filtered out: Title '{vehicle.get('title')}' does not contain 'Salvage'")
                return None
            
            # 3. Filter by odometer (must be under 100,000 miles)
            odometer = vehicle.get('odometer', 'N/A')
            if odometer != 'N/A':
                try:
                    # Remove commas and convert to int
                    odometer_value = int(str(odometer).replace(',', '').replace(' ', ''))
                    if odometer_value >= 100000:
                        print(f"  ❌ Filtered out: Odometer {odometer_value:,} miles is >= 100,000")
                        return None
                except (ValueError, AttributeError):
                    # If odometer can't be parsed, skip this vehicle
                    print(f"  ❌ Filtered out: Odometer '{odometer}' cannot be parsed")
                    return None
            else:
                # If odometer is N/A, skip this vehicle (we only want vehicles with known odometer)
                print(f"  ❌ Filtered out: Odometer is N/A (we only want vehicles with known odometer)")
                return None
            
            # 4. Check for upcoming/future
            if body_text:
                upcoming_patterns = [
                    r'upcoming\s+auction',
                    r'future\s+sale',
                    r'scheduled\s+for\s+\d{4}',
                ]
                for pattern in upcoming_patterns:
                    if re.search(pattern, body_text, re.IGNORECASE):
                        print(f"  ❌ Filtered out: Upcoming/future auction")
                        return None
            
            return vehicle
            
        except Exception as e:
            print(f"Error scraping lot {lot_number}: {str(e)}")
            return None
    
    def scrape_multiple_lots(self, lot_numbers, limit=100):
        """Scrape multiple Copart lots (optimized for speed)"""
        vehicles = []
        
        if not self.page:
            return vehicles
        
        total_to_scrape = min(len(lot_numbers), limit)
        print(f"Scraping {total_to_scrape} Copart lots (optimized for speed)...")
        
        for i, lot_number in enumerate(lot_numbers[:limit], 1):
            try:
                vehicle = self.scrape_copart_lot(lot_number)
                if vehicle:
                    vehicles.append(vehicle)
                    # Shorter print message for speed
                    print(f"  [{i}/{total_to_scrape}] ✓ {lot_number}: {vehicle.get('year')} - {vehicle.get('location')}")
                else:
                    print(f"  [{i}/{total_to_scrape}] ✗ {lot_number}: Filtered")
                
                # Minimal delay - only if not last item
                if i < total_to_scrape:
                    time.sleep(0.1)  # Further reduced delay (from 0.2 to 0.1)
                
            except Exception as e:
                print(f"  [{i}/{total_to_scrape}] ✗ {lot_number}: Error")
                continue
        
        print(f"\n✅ Successfully scraped {len(vehicles)} vehicles from Copart")
        return vehicles


def extract_lot_numbers_from_bidcars():
    """Extract all lot numbers from bid.cars (DEPRECATED - not used)"""
    # This function is deprecated - we now use extract_vehicles_from_search_results
    print("Warning: extract_lot_numbers_from_bidcars is deprecated")
    return []


def scrape_copart_vehicles_from_lots(lot_numbers, limit=100):
    """Scrape vehicle data from Copart using lot numbers"""
    scraper = None
    try:
        scraper = CopartScraper()
        vehicles = scraper.scrape_multiple_lots(lot_numbers, limit=limit)
        return vehicles
    except Exception as e:
        print(f"Error scraping Copart: {str(e)}")
        return []
    finally:
        if scraper:
            scraper.close()


def scrape_copart_corolla(limit=100):
    """Main function to scrape Toyota Corolla data (OPTIMIZED - extracts all data from search page)
    
    NEW APPROACH: Extract all data directly from search results page - MUCH FASTER!
    No need to visit individual lot pages.
    """
    try:
        print("Extracting vehicle data directly from Copart search results...")
        print("       (Much faster - no individual page visits needed)")
        scraper = CopartScraper()
        try:
            vehicles = scraper.extract_vehicles_from_search_results(filter_by_location=False)
            print(f"Found {len(vehicles)} vehicles")
            
            # Limit results if needed
            if limit and len(vehicles) > limit:
                vehicles = vehicles[:limit]
                print(f"Limited to {limit} vehicles")
        finally:
            scraper.close()
        
        return vehicles
    except Exception as e:
        print(f"Scraping failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
