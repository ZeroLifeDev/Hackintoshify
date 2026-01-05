

import ssl
import gzip
import plistlib
import io
import sys
from urllib.request import Request, urlopen

CATALOG_URL = "https://swscan.apple.com/content/catalogs/others/index-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"

def get_catalog():
    print("Downloading catalog...")
    context = ssl._create_unverified_context()
    req = Request(CATALOG_URL, headers={"User-Agent": "SoftwareUpdate/6 (Macintosh; Mac OS X 10.15.7)"})
    
    response = urlopen(req, context=context)
    data = response.read()
    
    print("Downloaded " + str(len(data)) + " bytes")
    
    try:
        if hasattr(plistlib, 'loads'):
            root = plistlib.loads(data)
        else:
            # Python 2 fallback or old 3
            try:
                # Python 3 < 3.9 might need from bytes
                root = plistlib.readPlistFromBytes(data)
            except:
                 # Python 2
                 import StringIO
                 root = plistlib.readPlist(StringIO.StringIO(data))
        print("Plist parsed successfully")
        return root
    except Exception as e:
        print("Plist parse failed: " + str(e))
        return None

def find_products(root):
    products = root.get('Products', {})
    print("Found " + str(len(products)) + " products")
    
    found_versions = []
    
    for product_id, product_data in products.items():
        packages = product_data.get('Packages', [])
        has_recovery = False
        base_system_url = None
        
        for pkg in packages:
            url = pkg.get('URL', '')
            if 'BaseSystem.dmg' in url:
                has_recovery = True
                base_system_url = url
                break

        if has_recovery and base_system_url:
            found_versions.append((product_id, base_system_url))
            
    print("Found " + str(len(found_versions)) + " recovery images")
    return found_versions

if __name__ == "__main__":
    root = get_catalog()
    if root:
        find_products(root)

