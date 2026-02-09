"""
Copart Toyota Corolla Scraper
Scrapes vehicle data from bid.cars and Copart with strict filtering
"""
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


class CopartScraper:
    """Main scraper class for Copart vehicles"""
    
    def __init__(self):
        self.driver = None
        # Don't initialize driver on creation - do it lazily when needed
    
    def setup_driver(self):
        """Setup Chrome driver with Cloudflare bypass options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Check for Chrome/Chromium in cloud environments (Render, Heroku, etc.)
        chrome_bin = os.environ.get('CHROME_BIN', None)
        if chrome_bin and os.path.isfile(chrome_bin):
            chrome_options.binary_location = chrome_bin
            print(f"Using Chrome binary from environment: {chrome_bin}")
        
        # Check for ChromeDriver path in environment (cloud platforms)
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', None)
        
        try:
            driver_path = None
            
            # Priority 1: Use environment variable path (cloud platforms)
            if chromedriver_path and os.path.isfile(chromedriver_path):
                driver_path = chromedriver_path
                print(f"Using ChromeDriver from environment: {chromedriver_path}")
            
            # Priority 2: Try known local ChromeDriver locations
            if not driver_path:
                known_paths = [
                    "/Users/lmd/.wdm/drivers/chromedriver/mac64/144.0.7559.96/chromedriver-mac-arm64/chromedriver",
                    "/usr/bin/chromedriver",
                    "/usr/local/bin/chromedriver",
                ]
                
                for path in known_paths:
                    if os.path.isfile(path):
                        try:
                            with open(path, 'rb') as f:
                                header = f.read(4)
                                if header and len(header) == 4:
                                    driver_path = path
                                    print(f"Using ChromeDriver from known path: {path}")
                                    break
                        except:
                            continue
            
            # Priority 3: Use webdriver-manager (fallback)
            if not driver_path:
                print("ChromeDriver not found in known paths, using webdriver-manager...")
                try:
                    driver_path = ChromeDriverManager().install()
                    print(f"ChromeDriver installed via webdriver-manager: {driver_path}")
                except Exception as e:
                    print(f"webdriver-manager failed: {e}")
                    raise Exception(f"Could not install ChromeDriver. Error: {e}")
            
            if not driver_path:
                raise Exception("ChromeDriver path not found and could not be installed")
            
            # Create service and driver
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ ChromeDriver initialized successfully")
            
            # Execute script to hide webdriver property
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
        except Exception as e:
            error_msg = f"Error setting up ChromeDriver: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            raise Exception(f"{error_msg}. Make sure Chrome/Chromium and ChromeDriver are installed.")
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def extract_vehicles_from_search_url(self, search_url, limit=20, description=""):
        """Extract all vehicle data directly from search results page (MUCH FASTER)"""
        vehicles = []
        
        # Initialize driver if not already done
        if not self.driver:
            try:
                print("Initializing ChromeDriver...")
                self.setup_driver()
                if not self.driver:
                    print("❌ ChromeDriver initialization failed - driver is None")
                    return vehicles
            except Exception as e:
                print(f"❌ Error initializing ChromeDriver: {e}")
                import traceback
                traceback.print_exc()
                return vehicles
        
        if not self.driver:
            print("❌ No ChromeDriver available - cannot scrape")
            return vehicles
        
        try:
            print(f"Navigating to Copart search results ({description})...")
            self.driver.get(search_url)
            
            # Wait for page to load
            print("Waiting for page to load...")
            time.sleep(5)
            
            # Wait for content
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except:
                pass
            
            time.sleep(2)
            
            page_source = self.driver.page_source
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
            "sale_info": "N/A"
        }
        
        row_text = row_element.get_text()
        row_html = str(row_element)
        
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
        
        # Initialize driver if not already done
        if not self.driver:
            try:
                self.setup_driver()
            except Exception as e:
                print(f"Error initializing ChromeDriver: {e}")
                return all_vehicles
        
        if not self.driver:
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
            
            # Filter vehicles by location and title
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
                
                filtered_vehicles.append(vehicle)
            
            print(f"\n✅ Total vehicles extracted: {len(all_vehicles)}")
            print(f"   - From MD/DC/NJ: {len(vehicles_1)}")
            print(f"   - From NY: {len(vehicles_2)}")
            print(f"   - After filtering: {len(filtered_vehicles)}")
            
            return filtered_vehicles
            
        except Exception as e:
            print(f"Error extracting vehicles: {str(e)}")
            import traceback
            traceback.print_exc()
            return all_vehicles
            
            # Wait for page to load (Copart may have Cloudflare or login requirements)
            print("Waiting for page to load...")
            time.sleep(10)  # Wait longer for Copart to fully load
            
            # Wait for content - Copart uses different selectors
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/lot/'], tr[data-lot-number], .lot-row"))
                )
            except:
                time.sleep(5)  # Additional wait if selector not found
            
            # Get rendered page text (after JavaScript execution)
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
            except:
                page_text = ""
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract lot numbers using "Lot #" tag and Location/Lane from Copart search results
            lot_numbers_found = set()
            lot_data_list = []  # Store lot number with Location/Lane info
            
            location_lane_patterns = [
                r'(?:Location\s*/\s*Lane|Location/Lane)[:\s]+[^<\n]{0,100}?([A-Z]{2})\b',
                r'(?:Location\s*/\s*Lane|Location/Lane)[:\s]+[^<\n]{0,100}?(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)\b',
                r'Lane[:\s]+[^<\n]{0,100}?(MD|NJ|DC|NY|Maryland|New Jersey|District of Columbia|New York)\b',
            ]
            
            # Method 1: Extract from "Lot #" tag - PRIMARY METHOD
            lot_hash_elements = soup.find_all(string=re.compile(r'Lot\s*#', re.IGNORECASE))
            for elem in lot_hash_elements:
                # Get parent element and its siblings to find lot number
                parent = elem.find_parent()
                if parent:
                    # Get text from parent and nearby elements
                    parent_text = parent.get_text()
                    # Also check next sibling
                    next_sibling = parent.find_next_sibling()
                    if next_sibling:
                        parent_text += ' ' + next_sibling.get_text()
                    # Check parent's parent (table cell or row)
                    grandparent = parent.find_parent()
                    if grandparent:
                        parent_text += ' ' + grandparent.get_text()
                    
                    # Extract lot number near "Lot #"
                    # Pattern: "Lot #" followed by 8 digits
                    lot_match = re.search(r'Lot\s*#\s*:?\s*(\d{8})', parent_text, re.IGNORECASE)
                    if lot_match:
                        lot_num = f'1-{lot_match.group(1)}'
                        if re.match(r'^1-\d{8}$', lot_num):
                            # Extract Location/Lane from same context
                            location_lane_state = "N/A"
                            
                            # Look for Location/Lane in the same context
                            for pattern in location_lane_patterns:
                                lane_match = re.search(pattern, parent_text, re.IGNORECASE)
                                if lane_match:
                                    state_text = lane_match.group(1).strip().upper()
                                    if state_text in ['MD', 'MARYLAND']:
                                        location_lane_state = 'MD'
                                        break
                                    elif state_text in ['NJ', 'NEW JERSEY']:
                                        location_lane_state = 'NJ'
                                        break
                                    elif state_text in ['DC', 'DISTRICT OF COLUMBIA']:
                                        location_lane_state = 'DC'
                                        break
                                    elif state_text in ['NY', 'NEW YORK']:
                                        location_lane_state = 'NY'
                                        break
                            
                            # If filtering by location, check Location/Lane
                            if filter_by_location:
                                if location_lane_state in ['MD', 'NJ', 'DC', 'NY']:
                                    lot_numbers_found.add(lot_num)
                                    lot_data_list.append({
                                        'lot_number': lot_num,
                                        'location_lane': location_lane_state
                                    })
                            else:
                                # No filtering, add all lots
                                lot_numbers_found.add(lot_num)
                                lot_data_list.append({
                                    'lot_number': lot_num,
                                    'location_lane': location_lane_state
                                })
            
            # Method 2: Extract from table rows (if "Lot #" method didn't find enough)
            if len(lot_numbers_found) < 10:
                table_rows = soup.find_all('tr')
                for row in table_rows:
                    row_text = row.get_text()
                    # Look for "Lot #" in row
                    if re.search(r'Lot\s*#', row_text, re.IGNORECASE):
                        lot_match = re.search(r'Lot\s*#\s*:?\s*(\d{8})', row_text, re.IGNORECASE)
                        if lot_match:
                            lot_num = f'1-{lot_match.group(1)}'
                            if re.match(r'^1-\d{8}$', lot_num):
                                # Extract Location/Lane from row
                                location_lane_state = "N/A"
                                for pattern in location_lane_patterns:
                                    lane_match = re.search(pattern, row_text, re.IGNORECASE)
                                    if lane_match:
                                        state_text = lane_match.group(1).strip().upper()
                                        if state_text in ['MD', 'MARYLAND']:
                                            location_lane_state = 'MD'
                                            break
                                        elif state_text in ['NJ', 'NEW JERSEY']:
                                            location_lane_state = 'NJ'
                                            break
                                        elif state_text in ['DC', 'DISTRICT OF COLUMBIA']:
                                            location_lane_state = 'DC'
                                            break
                                
                                # Search URL already filtered for MD/DC/NJ/NY, so add all lots
                                lot_numbers_found.add(lot_num)
                                lot_data_list.append({
                                    'lot_number': lot_num,
                                    'location_lane': location_lane_state
                                })
            
            # Method 3: Extract from links (href="/lot/XXXXX") - FALLBACK
            if not lot_numbers_found:
                lot_links = soup.find_all('a', href=re.compile(r'/lot/\d+'))
                for link in lot_links:
                    href = link.get('href', '')
                    match = re.search(r'/lot/(\d{8})', href)
                    if match:
                        lot_num = f'1-{match.group(1)}'
                        if re.match(r'^1-\d{8}$', lot_num):
                            # Get parent context for Location/Lane
                            parent = link.find_parent()
                            location_lane_state = "N/A"
                            
                            if parent:
                                parent_text = parent.get_text()
                                # Look for Location/Lane
                                for pattern in location_lane_patterns:
                                    lane_match = re.search(pattern, parent_text, re.IGNORECASE)
                                    if lane_match:
                                        state_text = lane_match.group(1).strip().upper()
                                        if state_text in ['MD', 'MARYLAND']:
                                            location_lane_state = 'MD'
                                            break
                                        elif state_text in ['NJ', 'NEW JERSEY']:
                                            location_lane_state = 'NJ'
                                            break
                                        elif state_text in ['DC', 'DISTRICT OF COLUMBIA']:
                                            location_lane_state = 'DC'
                                            break
                            
                            # Search URL already filtered for MD/DC/NJ, so add all lots
                            lot_numbers_found.add(lot_num)
                            lot_data_list.append({
                                'lot_number': lot_num,
                                'location_lane': location_lane_state
                            })
            
            # Method 2: Extract from data attributes (data-lot-number, data-lot, etc.)
            lot_elements = soup.find_all(attrs={'data-lot-number': True})
            for element in lot_elements:
                lot_num = element.get('data-lot-number', '').strip()
                if lot_num:
                    # Add "1-" prefix if not present
                    if not lot_num.startswith('1-'):
                        lot_num = f'1-{lot_num}'
                    if re.match(r'^1-\d{8}$', lot_num):
                        lot_numbers_found.add(lot_num)
            
            # Method 3: Extract from element IDs (format: 1-XXXXXXXX)
            lot_elements = soup.find_all('div', id=True)
            for element in lot_elements:
                element_id = element.get('id', '')
                if element_id and re.match(r'^1-\d{8}$', element_id):
                    lot_numbers_found.add(element_id)
            
            # Method 4: Extract from page source using regex
            lot_pattern = r'\b(1-\d{8})\b'
            found_lots = re.findall(lot_pattern, page_source)
            for lot in found_lots:
                lot_numbers_found.add(lot)
            
            # Convert set to list
            lot_numbers = list(lot_numbers_found)
            
            # Try to load more pages (Copart pagination)
            page_count = 1
            max_pages = 50  # Increased to get more results
            previous_count = len(lot_numbers_found)
            
            while page_count < max_pages:
                try:
                    # Multiple strategies to find Next button
                    next_button = None
                    
                    # Strategy 1: Look for pagination next button by various selectors
                    next_selectors = [
                        'a[data-uname="lotsearchPaginationNext"]',
                        '.pagination-next',
                        'a.pagination-next',
                        'button.pagination-next',
                        'a[aria-label*="Next"]',
                        'button[aria-label*="Next"]',
                        'a:contains("Next")',
                        'button:contains("Next")',
                        '.next-page',
                        'a.next',
                        'button.next'
                    ]
                    
                    for selector in next_selectors:
                        try:
                            if ':contains' in selector:
                                # Use XPath for text contains
                                text = selector.split(':contains("')[1].split('")')[0]
                                next_button = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{text}')] | //button[contains(text(), '{text}')]")
                            else:
                                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            
                            if next_button and next_button.is_enabled() and next_button.is_displayed():
                                break
                        except:
                            continue
                    
                    # Strategy 2: Look for page number links and click the next one
                    if not next_button:
                        try:
                            # Find current page number
                            page_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-uname*="pagination"], .pagination a, .page-link')
                            current_page = page_count
                            for link in page_links:
                                link_text = link.text.strip()
                                if link_text.isdigit() and int(link_text) == current_page + 1:
                                    next_button = link
                                    break
                        except:
                            pass
                    
                    # Strategy 3: Try scrolling and waiting for dynamic content
                    if not next_button:
                        # Scroll to bottom to trigger lazy loading
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        # Re-extract lots from current page (might have loaded more)
                        page_source = self.driver.page_source
                        soup = BeautifulSoup(page_source, 'html.parser')
                        
                        # Extract lots using all methods again
                        lot_hash_elements = soup.find_all(string=re.compile(r'Lot\s*#', re.IGNORECASE))
                        for elem in lot_hash_elements:
                            parent = elem.find_parent()
                            if parent:
                                parent_text = parent.get_text()
                                lot_match = re.search(r'Lot\s*#\s*:?\s*(\d{8})', parent_text, re.IGNORECASE)
                                if lot_match:
                                    lot_num = f'1-{lot_match.group(1)}'
                                    if re.match(r'^1-\d{8}$', lot_num):
                                        lot_numbers_found.add(lot_num)
                        
                        # Check if we got new lots
                        current_count = len(lot_numbers_found)
                        if current_count > previous_count:
                            previous_count = current_count
                            page_count += 1
                            continue
                        else:
                            # No new lots, try to find next button one more time
                            pass
                    
                    # If we found a next button, click it
                    if next_button:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                            time.sleep(1)
                            self.driver.execute_script("arguments[0].click();", next_button)
                            time.sleep(5)  # Wait longer for page to load
                            
                            # Re-extract lots from new page
                            page_source = self.driver.page_source
                            soup = BeautifulSoup(page_source, 'html.parser')
                            
                            # Extract using all methods
                            lot_hash_elements = soup.find_all(string=re.compile(r'Lot\s*#', re.IGNORECASE))
                            for elem in lot_hash_elements:
                                parent = elem.find_parent()
                                if parent:
                                    parent_text = parent.get_text()
                                    lot_match = re.search(r'Lot\s*#\s*:?\s*(\d{8})', parent_text, re.IGNORECASE)
                                    if lot_match:
                                        lot_num = f'1-{lot_match.group(1)}'
                                        if re.match(r'^1-\d{8}$', lot_num):
                                            lot_numbers_found.add(lot_num)
                            
                            # Also extract from links
                            new_lot_links = soup.find_all('a', href=re.compile(r'/lot/\d+'))
                            for link in new_lot_links:
                                href = link.get('href', '')
                                match = re.search(r'/lot/(\d+)', href)
                                if match:
                                    lot_num = f'1-{match.group(1)}'
                                    if re.match(r'^1-\d{8}$', lot_num):
                                        lot_numbers_found.add(lot_num)
                            
                            # Extract from data attributes
                            new_lot_elements = soup.find_all(attrs={'data-lot-number': True})
                            for element in new_lot_elements:
                                lot_num = element.get('data-lot-number', '').strip()
                                if lot_num:
                                    if not lot_num.startswith('1-'):
                                        lot_num = f'1-{lot_num}'
                                    if re.match(r'^1-\d{8}$', lot_num):
                                        lot_numbers_found.add(lot_num)
                            
                            # Extract from page source regex
                            lot_pattern = r'\b(1-\d{8})\b'
                            found_lots = re.findall(lot_pattern, page_source)
                            for lot in found_lots:
                                lot_numbers_found.add(lot)
                            
                            current_count = len(lot_numbers_found)
                            if current_count > previous_count:
                                print(f"  Page {page_count + 1}: Found {current_count - previous_count} new lots (Total: {current_count})")
                                previous_count = current_count
                                page_count += 1
                            else:
                                # No new lots found, stop pagination
                                print(f"  No new lots on page {page_count + 1}, stopping pagination")
                                break
                        except Exception as e:
                            print(f"  Error clicking next button: {str(e)}")
                            break
                    else:
                        # No next button found, stop pagination
                        print(f"  No next button found on page {page_count}, stopping pagination")
                        break
                except Exception as e:
                    print(f"  Error during pagination: {str(e)}")
                    break
            
            unique_lots = sorted(list(set(lot_numbers_found)))
            
            # Initialize cache (Location/Lane will be extracted from individual lot pages)
            self.lot_data_cache = {}
            
            print(f"Found {len(unique_lots)} unique lot numbers from Copart search results")
            print("Note: Search URL already filtered for MD/DC/NJ/NY states")
            print("      Individual lot pages will be scraped for full details")
            
            return unique_lots
            
        except Exception as e:
            print(f"Error extracting lot numbers: {str(e)}")
            return lot_numbers
    
    def scrape_copart_lot(self, lot_number):
        """Scrape a single Copart lot page"""
        if not self.driver:
            return None
        
        try:
            # Remove "1-" prefix if present
            if lot_number.startswith('1-'):
                lot_number = lot_number[2:]
            
            copart_url = f"https://www.copart.com/lot/{lot_number}"
            print(f"Scraping Copart lot: {lot_number}")
            
            self.driver.get(copart_url)
            time.sleep(2)  # Reduced from 3 to 2 seconds
            
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            time.sleep(1)  # Reduced from 2 to 1 second
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Optimized body text extraction using JavaScript
            try:
                body_text = self.driver.execute_script("return document.body.innerText || document.body.textContent || ''")
            except:
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
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
                "url": copart_url
            }
            
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
            
            # 3. Check for upcoming/future
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
        
        if not self.driver:
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
    """Extract all lot numbers from bid.cars"""
    scraper = None
    try:
        scraper = CopartScraper()
        lot_numbers = scraper.extract_lot_numbers_from_bidcars()
        return lot_numbers
    except Exception as e:
        print(f"Error extracting lot numbers: {str(e)}")
        return []
    finally:
        if scraper:
            scraper.close()


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
