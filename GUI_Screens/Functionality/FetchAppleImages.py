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
# Comprehensive list of catalogs to ensure we find EVERYTHING (Dev, Beta, Public)
CATALOG_URLS = [
    # macOS 15 / 14 / 13 / 12 / 11 (Big Sur and newer use 10.16 format in catalogs)
    "https://swscan.apple.com/content/catalogs/others/index-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
    "https://swscan.apple.com/content/catalogs/others/index-10.16seed-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
    "https://swscan.apple.com/content/catalogs/others/index-10.16customerseed-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
    "https://swscan.apple.com/content/catalogs/others/index-10.16developerseed-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
    
    # macOS 10.15 (Catalina) specific
    "https://swscan.apple.com/content/catalogs/others/index-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
    "https://swscan.apple.com/content/catalogs/others/index-10.15seed-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
    
    # macOS 10.14 (Mojave) specific
    "https://swscan.apple.com/content/catalogs/others/index-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
    
    # macOS 10.13 (High Sierra)
    "https://swscan.apple.com/content/catalogs/others/index-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
]

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

# Static Fallback - CLEARED to avoid 403s on dead links. We rely on the Catalog now.
STATIC_ENTRIES = []

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

    def format_name(self, name, version):
        """Appends version if not present"""
        if version and version not in name:
            return f"{name} ({version})"
        return name

    def fetch_images_from_catalog(self):
        # 1. Download Catalog (Try multiple if needed)
        candidates = []
        seen_urls = set()
        
        for url in CATALOG_URLS:
            if self.status_callback: self.status_callback(f"Scanning catalog...")
            if self.verbose: print(f"Checking {url}...")
            
            data = get_url_content(url)
            if not data:
                continue
                
            try:
                root = plistlib.loads(data)
            except Exception as e:
                if self.verbose: print(f"Catalog parse error: {e}")
                continue

            products = root.get('Products', {})
            count_in_this = 0
            
            for pid, pdata in products.items():
                packages = pdata.get('Packages', [])
                base_system_url = None
                chunklist_url = None
                
                for pkg in packages:
                    u = pkg.get('URL', '')
                    if u.endswith("BaseSystem.dmg"):
                        base_system_url = u
                    elif u.endswith("BaseSystem.chunklist"):
                        chunklist_url = u
                
                if base_system_url and base_system_url not in seen_urls:
                    seen_urls.add(base_system_url)
                    
                    meta_url = pdata.get('ServerMetadataURL')
                    date = pdata.get('PostDate') 
                    
                    # Try to find version info in Dist (better than name)
                    # or extended meta
                    
                    candidates.append({
                        'id': pid,
                        'url': base_system_url,
                        'chunklist': chunklist_url,
                        'meta_url': meta_url,
                        'date': date
                    })
                    count_in_this += 1
            
            if self.verbose: print(f"Found {count_in_this} candidates in this catalog")

        if not candidates:
            if self.verbose: print("No images found in any catalog")
            return self.apple_images 

        if self.status_callback: self.status_callback(f"Found total {len(candidates)} versions. Parsing...")
        
        # 3. Resolve Names (Threaded)
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
                            cand['name'] = name
                            # We can cache specifically for this session 
                        else:
                            cand['name'] = f"macOS Installer ({cand['id']})"
                    except:
                        cand['name'] = f"macOS Installer ({cand['id']})"
                    final_list.append(cand)

        # 4. Clean up and Deduplicate
        # Strategy: Keep distinct versions.
        # If we have multiple entries with EXACT SAME name, we keep the one with latest date.
        # But if names are different (e.g. 15.1 vs 15.0), we keep both.
        
        best_versions = {} # "Name" -> {data}
        
        for item in final_list:
            name = item['name']
            
            # Improve name consistency
            # If name is generic "macOS Installer", look at ID to guess?
            
            # Unique Key: Name
            # If "macOS 15: Sequoia" appears twice (for 15.0 and 15.1?), we might lose one.
            # Ideally we want the version string. 
            # If name doesn't distinguish, append ID.
            
            key = name
            
            # Temporary: Allow duplicates if IDs are different? 
            # No, that clutters nicely named lists.
            # Users want "All possible versions".
            # So let's append ID to name if it's generic, or trust name uniqueness.
            
            # Actually, let's keep everything but sort nicely.
            # But the user complained about "only 4 versions".
            # This was because I deduplicated by simplified name.
            # Now I am NOT calling simplify_name.
            
            # Just dedupe by exact name match.
            if key not in best_versions:
                 best_versions[key] = item
            else:
                 # Check date
                 existing_date = best_versions[key].get('date', datetime.datetime.min)
                 new_date = item.get('date', datetime.datetime.min)
                 # Handle None
                 if not existing_date: existing_date = datetime.datetime.min
                 if not new_date: new_date = datetime.datetime.min
                 
                 if new_date > existing_date:
                     best_versions[key] = item
        
        valid_images = list(best_versions.values())
        
        # Sort by Name (descending to get 15, 14, 13...)
        def sort_key(x):
            n = x['name']
            try:
                # Find version number
                import re
                match = re.search(r'(\d+(\.\d+)?)', n)
                if match:
                    val = float(match.group(1))
                    if val < 20: # 10.15 -> 10.15. 15 -> 15.
                         return val
                    # 10.15 is 10.15. 15 is 15.
                    # 15 > 10.15. Correct.
            except:
                pass
            return 0
            
        valid_images.sort(key=sort_key, reverse=True)
            
        self.apple_images = valid_images
        self.save_cache()
        
        return self.apple_images

if __name__ == "__main__":
    print("FetchAppleImages Standalone Test")
    f = FetchAppleImages(verbose=True)
    for img in f.apple_images:
        print(f"{img['name']} - {img['url']}")
