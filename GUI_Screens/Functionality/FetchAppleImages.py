
import sys
import os
import json
import ssl
import plistlib
import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

# ---------------------------------------------------------
# PRODUCT IDENTIFIERS MAPPING (For fallback when Metadata fails)
# ---------------------------------------------------------
PRODUCT_NAMES = {
    # Sequoia (15)
    "089-70987": "macOS 15: Sequoia (2025)", 
    "093-99065": "macOS 15: Sequoia",
    "093-52107": "macOS 15: Sequoia",
    "093-34000": "macOS 15: Sequoia",
    
    # Sonoma (14)
    "089-71265": "macOS 14: Sonoma (2025)",
    "093-92756": "macOS 14: Sonoma",
    "093-53928": "macOS 14: Sonoma",
    "093-33776": "macOS 14: Sonoma",
    "062-87588": "macOS 14: Sonoma",
    
    # Ventura (13)
    "093-22004": "macOS 13: Ventura",
    "042-23155": "macOS 13: Ventura",
    
    # Monterey (12)
    "052-60131": "macOS 12: Monterey",
    "093-37367": "macOS 12: Monterey",
    
    # Big Sur (11)
    "042-45246": "macOS 11: Big Sur",
    "001-79699": "macOS 11: Big Sur",
    
    # Catalina (10.15)
    "041-88800": "macOS 10.15: Catalina",
    "061-26589": "macOS 10.15: Catalina",
    "001-68446": "macOS 10.15.7: Catalina",
    "001-57224": "macOS 10.15.7: Catalina", 
    "001-51042": "macOS 10.15.7: Catalina",
    "001-36801": "macOS 10.15.6: Catalina",
    "001-36735": "macOS 10.15.6: Catalina",
    "001-15219": "macOS 10.15.5: Catalina",
    "001-04366": "macOS 10.15.4: Catalina",
    
    # Mojave (10.14)
    "061-86291": "macOS 10.14.6: Mojave",
    "041-91758": "macOS 10.14.6: Mojave",
    "061-26578": "macOS 10.14.6: Mojave",
}

CACHE_FILE = "recovery_cache.json"

def get_url_content(url, headers=None):
    if headers is None:
        headers = {
            "User-Agent": "SoftwareUpdate/6 (Macintosh; Mac OS X 15.0)"
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

def generate_catalog_urls():
    urls = []
    # Scan from 26 (Tahoe) down to 11 (Big Sur)
    versions = range(26, 10, -1) 
    types = ["seed", "beta", "customerseed", ""]
    
    legacy_suffix = "-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
    
    for v in versions:
        chain_nums = [str(x) for x in range(v, 10, -1)]
        chain = "-".join(chain_nums)
        for t in types:
            url = f"https://swscan.apple.com/content/catalogs/others/index-{v}{t}-{chain}{legacy_suffix}"
            urls.append(url)
            
    urls.append("https://swscan.apple.com/content/catalogs/others/index-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog")
    urls.append("https://swscan.apple.com/content/catalogs/others/index-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog")
    urls.append("https://swscan.apple.com/content/catalogs/others/index-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog")
    
    return urls

CATALOG_URLS = generate_catalog_urls()

class FetchAppleImages:
    def __init__(self, verbose=False, use_cache=True, status_callback=None):
        self.verbose = verbose
        self.use_cache = use_cache
        self.status_callback = status_callback
        self.apple_images = []
        self.seen_products = set()

        if self.use_cache:
            if self.status_callback: self.status_callback("Checking cache...")
            self.load_cache()

        if not self.apple_images or not self.use_cache:
            try:
                if self.status_callback: self.status_callback("Scanning Apple Catalogs...")
                self.fetch_images_from_catalog()
            except Exception as e:
                pass
        
        # Always sort at the end
        self.sort_images()

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.apple_images = data
            except:
                pass

    def save_cache(self):
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.apple_images, f, indent=4, default=str)
        except:
            pass

    def sort_images(self):
        def parse_date(x):
            d = x.get('date')
            if isinstance(d, datetime.datetime): return d
            if isinstance(d, str):
                try: return datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
                except: 
                    try: return datetime.datetime.strptime(d, "%Y-%m-%d")
                    except: pass
            return datetime.datetime.min

        def get_version_score(item):
            name = item.get('name', '').lower()
            if "tahoe" in name or "16." in name or "macos 16" in name: return 16
            if "sequoia" in name or "15." in name or "macos 15" in name: return 15
            if "sonoma" in name or "14." in name or "macos 14" in name: return 14
            if "ventura" in name or "13." in name or "macos 13" in name: return 13
            if "monterey" in name or "12." in name or "macos 12" in name: return 12
            if "big sur" in name or "11." in name or "macos 11" in name: return 11
            if "catalina" in name or "10.15" in name: return 10.15
            if "mojave" in name or "10.14" in name: return 10.14
            if "high sierra" in name or "10.13" in name: return 10.13
            return 0

        # Sort primarily by Version Score (Descending), then by Date (Descending)
        self.apple_images.sort(key=lambda x: (get_version_score(x), parse_date(x)), reverse=True)

    def get_product_name(self, pid, distributions, server_metadata_url):
        if pid in PRODUCT_NAMES:
            return PRODUCT_NAMES[pid]

        name = None
        dist_url = distributions.get('English') or distributions.get('en')
        
        if dist_url:
            try:
                content = get_url_content(dist_url)
                if content:
                    text = content.decode('utf-8', errors='ignore')
                    m = re.search(r'<title>(.*?)</title>', text, re.IGNORECASE)
                    if m:
                        candidate = m.group(1).strip()
                        if candidate and candidate != "SU_TITLE":
                            name = candidate
                    
                    if not name or name == "SU_TITLE":
                        if "macOSSequoia" in text or "macOS Sequoia" in text:
                            name = "macOS 15: Sequoia"
                        elif "macOSSonoma" in text or "macOS Sonoma" in text:
                            name = "macOS 14: Sonoma"
                        elif "macOSVentura" in text or "macOS Ventura" in text:
                            name = "macOS 13: Ventura"
                        elif "macOSMonterey" in text or "macOS Monterey" in text:
                            name = "macOS 12: Monterey"
                        elif "macOSBigSur" in text or "macOS Big Sur" in text:
                            name = "macOS 11: Big Sur"
            except:
                pass
        
        if name: return name

        if server_metadata_url:
            try:
                data = get_url_content(server_metadata_url)
                if data:
                    if hasattr(plistlib, 'loads'):
                        plist = plistlib.loads(data)
                    else:
                        plist = plistlib.readPlistFromBytes(data)
                    candidate = plist.get('localization', {}).get('English', {}).get('title')
                    if candidate and candidate != "SU_TITLE":
                        name = candidate
            except:
                pass
        
        if name: return name
        
        return f"macOS Installer ({pid})"

    def fetch_images_from_catalog(self):
        raw_candidates = []
        
        total_catalogs = len(CATALOG_URLS)
        
        for idx, url in enumerate(CATALOG_URLS):
            if self.status_callback: 
                self.status_callback(f"Scanning Catalog {idx+1}/{total_catalogs}...")
            
            data = get_url_content(url)
            if not data: continue
            
            try:
                if hasattr(plistlib, 'loads'):
                     root = plistlib.loads(data)
                else:
                     root = plistlib.readPlistFromBytes(data)
            except:
                continue
                
            products = root.get('Products', {})
            
            for pid, pdata in products.items():
                if pid in self.seen_products: continue

                packages = pdata.get('Packages', [])
                valid_candidate = False
                base_system_url = None
                chunklist_url = None
                is_full_installer = False
                
                for pkg in packages:
                    u = pkg.get('URL', '')
                    u_low = u.lower()
                    
                    if "basesystem" in u_low:
                        base_system_url = u
                        valid_candidate = True
                    elif "installassistant" in u_low and ".pkg" in u_low:
                        if not base_system_url:
                            base_system_url = u
                            is_full_installer = True
                            valid_candidate = True
                    
                    if "chunklist" in u_low:
                        chunklist_url = u
                
                if valid_candidate and base_system_url:
                    self.seen_products.add(pid)
                    date = pdata.get('PostDate')
                    
                    raw_candidates.append({
                        'id': pid,
                        'url': base_system_url,
                        'chunklist': chunklist_url,
                        'dist': pdata.get('Distributions', {}),
                        'meta_url': pdata.get('ServerMetadataURL'),
                        'date': date,
                        'full_installer': is_full_installer
                    })
        
        if not raw_candidates:
            return

        if self.status_callback: self.status_callback(f"Resolving names for {len(raw_candidates)} versions...")

        final_list = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_cand = {
                executor.submit(self.get_product_name, c['id'], c['dist'], c['meta_url']): c 
                for c in raw_candidates
            }
            
            for future in as_completed(future_to_cand):
                c = future_to_cand[future]
                try:
                    name = future.result()
                    c['name'] = name
                except:
                    c['name'] = f"macOS Installer ({c['id']})"
                
                if c['name'] == "SU_TITLE":
                     c['name'] = f"macOS Installer ({c['id']})"
                     
                final_list.append(c)
        
        formatted = []
        for item in final_list:
            name = item['name']
            
            if name == "SU_TITLE": name = f"macOS Installer ({item['id']})"

            if item.get('full_installer'):
                name = f"{name} (Full Installer)"

            date = item.get('date')
            if date:
                dstr = str(date).split()[0]
                name = f"{name} ({dstr})"
            else:
                name = f"{name} ({item['id']})"
            
            item['name'] = name
            formatted.append(item)
            
        self.apple_images = formatted
        self.save_cache()

if __name__ == "__main__":
    print("FetchAppleImages Standalone Test")
    f = FetchAppleImages(verbose=True, use_cache=False)
    for img in f.apple_images:
        print(f"{img['name']}")
