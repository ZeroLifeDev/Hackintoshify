
import requests
import sys

# Suppress warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://swcdn.apple.com/content/downloads/25/22/093-37385/tc6397qpjd9cudicjkvu1ucrs11yr1rlcs/RecoveryImage/BaseSystem.dmg"

try:
    print("Checking " + url)
    headers = {'User-Agent': 'InternetRecovery/1.0'}
    r = requests.head(url, headers=headers, verify=False, timeout=10)
    print("Status: " + str(r.status_code))
    print("Reason: " + str(r.reason))
except Exception as e:
    print("Error: " + str(e))
