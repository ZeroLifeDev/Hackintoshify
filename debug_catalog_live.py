import ssl
import sys
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request
import plistlib

URL_15 = "https://swscan.apple.com/content/catalogs/others/index-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
URL_14 = "https://swscan.apple.com/content/catalogs/others/index-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
URL_16_SEED = "https://swscan.apple.com/content/catalogs/others/index-16seed-16-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"

def check(url, label):
    print(f"\n--- Checking {label} ---")
    headers = {
        "User-Agent": "SoftwareUpdate/6 (Macintosh; Mac OS X 14.5)"
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        req = Request(url, headers=headers)
        resp = urlopen(req, context=ctx)
        print(f"Status: {resp.getcode()}")
        data = resp.read()
        print(f"Length: {len(data)}")
        
        if len(data) < 1000:
            print("Response too small.")
            print(data)
            return

        try:
            if hasattr(plistlib, 'loads'):
                root = plistlib.loads(data)
            else:
                root = plistlib.readPlistFromBytes(data)
        except Exception as e:
            print(f"Plist Parse Error: {e}")
            return
            
        prods = root.get('Products', {})
        print(f"Product Count: {len(prods)}")
        
        # Scan for ANY BaseSystem or InstallAssistant to see if they exist
        found_bs = 0
        found_ia = 0
        
        for pid, pdata in prods.items():
            pkgs = pdata.get('Packages', [])
            for pkg in pkgs:
                u = pkg.get('URL', '')
                if 'BaseSystem' in u: return # Stop spam, search confirmed
                    # We want to see if ANY is found
                if 'InstallAssistant' in u: found_ia += 1
        
        # Just print first 5 package URLs to verify structure
        print("Sample Packages:")
        count = 0
        for pid, pdata in prods.items():
            if count > 5: break
            pkgs = pdata.get('Packages', [])
            for pkg in pkgs:
                print(f"  {pkg.get('URL', '')}")
            count += 1

    except Exception as e:
        print(f"Request Error: {e}")

if __name__ == '__main__':
    check(URL_15, "macOS 15")
    check(URL_14, "macOS 14")
    check(URL_16_SEED, "macOS 16 Seed")
