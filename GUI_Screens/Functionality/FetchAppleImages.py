# GUI_Screens/Functionality/FetchAppleImages.py

"""
FetchAppleImages Functionality for Hackintoshify
Author: PanCakeeYT (Abdelrahman)
Date: December 2025
Updated: Jan 2026 (Catalog Support - Sequoia/Sonoma/Tahoe)
"""

import os
import sys
import random
import string
import time
import json
import ssl
import plistlib
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, HTTPError, urlopen
from urllib.parse import urlparse

# Constants
# Updated Catalog URL covering 15 (Sequoia), 14 (Sonoma), 13 (Ventura), 12, 11, etc.
CATALOG_URL = "https://swscan.apple.com/content/catalogs/others/index-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"

CACHE_FILE = "recovery_cache.json"

# Extensive Product ID to Name Mapping
# We can use this to normalize names
PRODUCT_NAMES = {
    # Sequoia (15)
    "093-37385": "macOS 15: Sequoia",
    "093-27888": "macOS 15: Sequoia",
    
    # Sonoma (14)
    "062-87588": "macOS 14: Sonoma",
    "071-78714": "macOS 14: Sonoma",
    
    # Ventura (13)
    "042-23155": "macOS 13: Ventura",
    "032-96585": "macOS 13: Ventura",
    
    # Monterey (12)
    "093-37367": "macOS 12: Monterey",
    "062-58679": "macOS 12: Monterey",
    
    # Big Sur (11)
    "001-79699": "macOS 11: Big Sur",
    "001-51031": "macOS 11: Big Sur",

    # Catalina (10.15)
    "041-88800": "macOS 10.15: Catalina",
    "061-26589": "macOS 10.15: Catalina", 
    "012-40515": "macOS 10.15: Catalina",

    # Mojave (10.14)
    "061-86291": "macOS 10.14: Mojave",
    "041-91758": "macOS 10.14: Mojave",
    "041-08708": "macOS 10.14: Mojave",

    # High Sierra (10.13)
    "091-34298": "macOS 10.13: High Sierra",
    "041-90855": "macOS 10.13: High Sierra",
    "031-18237": "macOS 10.13: High Sierra",
}

# Static Fallback / Custom Entries (e.g. Tahoe)
STATIC_ENTRIES = [
    {
        "id": "Custom-Tahoe", 
        "name": "macOS 26: Tahoe", 
        "url": "https://swcdn.apple.com/content/downloads/25/22/093-37385/tc6397qpjd9cudicjkvu1ucrs11yr1rlcs/RecoveryImage/BaseSystem.dmg", 
        "chunklist": "https://swcdn.apple.com/content/downloads/25/22/093-37385/tc6397qpjd9cudicjkvu1ucrs11yr1rlcs/RecoveryImage/BaseSystem.chunklist",
        "date": datetime.datetime.now() # Always new
    }
]

def get_url_content(url, headers=None):
    if headers is None:
        headers = {
            "User-Agent": "SoftwareUpdate/6 (Macintosh; Mac OS X 10.15.7)"
        }
    
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    req = Request(url, headers=headers)
    try:
        response = urlopen(req, context=context)
        return response.read()
    except Exception as e:
        return None

class FetchAppleImages:
    def __init__(self, verbose=False, use_cache=True, status_callback=None):
        self.verbose = verbose
        self.use_cache = use_cache
        self.status_callback = status_callback
        self.apple_images = []
        
        # Load cache first
        if self.use_cache:
            if self.status_callback: self.status_callback("Checking cache...")
            self.load_cache()

        try:
            if self.status_callback: self.status_callback("Connecting to Apple Catalogs...")
            self.fetch_images_from_catalog()
        except Exception as e:
             if self.verbose: print(f"Init failed: {e}")
             if self.status_callback: self.status_callback(f"Error: {e}")

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    self.apple_images = data
                    if self.verbose: print(f"Loaded {len(data)} images from cache.")
            except Exception as e:
                if self.verbose: print(f"Cache load failed: {e}")

    def save_cache(self):
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.apple_images, f, indent=4, default=str)
        except Exception as e:
            if self.verbose: print(f"Cache save failed: {e}")

    def fetch_metadata(self, pid, metadata_url):
        """Fetches localized name from ServerMetadata"""
        try:
            data = get_url_content(metadata_url)
            if not data: return None
            
            plist = plistlib.loads(data)
            # Try to get English title
            name = plist.get('localization', {}).get('English', {}).get('title')
            return (pid, name)
        except Exception:
            return None

    def simplify_name(self, name):
        """Normalizes names to a standard format"""
        name = name.strip()
        # Handle "macOS Sequoia" without version
        if "Sequioa" in name or "Sequoia" in name: 
            if "15" not in name: return "macOS 15: Sequoia"
        if "Sonoma" in name:
            if "14" not in name: return "macOS 14: Sonoma"
        if "Ventura" in name:
            if "13" not in name: return "macOS 13: Ventura"
        if "Monterey" in name:
            if "12" not in name: return "macOS 12: Monterey"
        if "Big Sur" in name:
            if "11" not in name: return "macOS 11: Big Sur"
        if "Catalina" in name:
            if "10.15" not in name: return "macOS 10.15: Catalina"
        if "Mojave" in name:
            if "10.14" not in name: return "macOS 10.14: Mojave"
        if "High Sierra" in name:
            if "10.13" not in name: return "macOS 10.13: High Sierra"
        return name

    def fetch_images_from_catalog(self):
        # 1. Download Catalog
        if self.status_callback: self.status_callback("Downloading Catalog (may take a moment)...")
        data = get_url_content(CATALOG_URL)
        if not data:
            if self.verbose: print("Failed to download catalog")
            return self.apple_images 
            
        try:
            root = plistlib.loads(data)
        except Exception as e:
            if self.verbose: print(f"Catalog parse error: {e}")
            return self.apple_images

        products = root.get('Products', {})
        candidates = []
        
        # 2. Filter for Recovery Images
        for pid, pdata in products.items():
            packages = pdata.get('Packages', [])
            base_system_url = None
            chunklist_url = None
            
            for pkg in packages:
                url = pkg.get('URL', '')
                if url.endswith("BaseSystem.dmg"):
                    base_system_url = url
                elif url.endswith("BaseSystem.chunklist"):
                    chunklist_url = url
            
            if base_system_url:
                meta_url = pdata.get('ServerMetadataURL')
                date = pdata.get('PostDate') 
                # keep date for sorting
                
                candidates.append({
                    'id': pid,
                    'url': base_system_url,
                    'chunklist': chunklist_url,
                    'meta_url': meta_url,
                    'date': date
                })

        if self.status_callback: self.status_callback(f"Found {len(candidates)} versions. Parsing...")
        
        # 3. Resolve Names (Threaded)
        # Use existing cache mapping or fetch
        final_list = []
        unknown_pids = []
        
        for cand in candidates:
            pid = cand['id']
            if pid in PRODUCT_NAMES:
                cand['name'] = PRODUCT_NAMES[pid]
                final_list.append(cand)
            else:
                unknown_pids.append(cand)
        
        # Fetch unknown metadata if needed
        if unknown_pids:
            if self.status_callback: self.status_callback(f"Resolving names for {len(unknown_pids)} new versions...")
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_cand = {}
                for cand in unknown_pids:
                    if cand['meta_url']:
                        f = executor.submit(self.fetch_metadata, cand['id'], cand['meta_url'])
                        future_to_cand[f] = cand
                    else:
                        cand['name'] = f"macOS Installer ({cand['id']})"
                        final_list.append(cand)
                
                for future in as_completed(future_to_cand):
                    cand = future_to_cand[future]
                    try:
                        res = future.result()
                        if res and res[1]:
                            name = res[1]
                            # Normalize name immediately
                            name = self.simplify_name(name)
                            cand['name'] = name
                            # PRODUCT_NAMES[cand['id']] = name # Dont cache globally to avoid pollution across runs if we want fresh
                        else:
                            cand['name'] = f"macOS Installer ({cand['id']})"
                    except:
                        cand['name'] = f"macOS Installer ({cand['id']})"
                    final_list.append(cand)

        # 4. Clean up and Deduplicate
        # Strategy: Group by Name. Keep the one with the LATEST Date.
        
        best_versions = {} # "macOS 15: Sequoia" -> {data}
        
        for item in final_list:
            name = item['name']
            # Normalize again just in case
            name = self.simplify_name(name)
            item['name'] = name # Update item
            
            # Date Check
            date = item.get('date')
            if not date: date = datetime.datetime.min
            
            if name not in best_versions:
                best_versions[name] = item
            else:
                # Compare dates
                existing_date = best_versions[name].get('date', datetime.datetime.min)
                if date > existing_date:
                    best_versions[name] = item
        
        # Convert back to list
        valid_images = list(best_versions.values())
        
        # Add Static Entries (Tahoe) if not present
        seen_names = set(img['name'] for img in valid_images)
        for static in STATIC_ENTRIES:
             if static['name'] not in seen_names:
                 valid_images.append(static)
        
        # Sort by Name (descending to get 15, 14, 13...)
        # We need a custom sort mechanism because "macOS 15" > "macOS 14" alpha sort works, 
        # but "macOS 10.15" vs "macOS 11" might be tricky naturally.
        # Actually alphabetical: "macOS 15" < "macOS 26" (Tahoe).
        # "macOS 15" vs "macOS 11". '15' > '11'.
        # "macOS 11" vs "macOS 10". '11' > '10'.
        # So clear string sort might mostly work, but let's be safe.
        
        def sort_key(x):
            n = x['name']
            # Extract version number for sorting
            parts = n.split()
            for p in parts:
                if p[0].isdigit():
                    # Check for 10.xx format
                    if "." in p:
                        return float(p.split(":")[0]) # 10.15
                    try:
                        val = float(p.replace(":", ""))
                        return val
                    except:
                        pass
            return 0
            
        valid_images.sort(key=sort_key, reverse=True)
            
        self.apple_images = valid_images
        self.save_cache()
        
        return self.apple_images
