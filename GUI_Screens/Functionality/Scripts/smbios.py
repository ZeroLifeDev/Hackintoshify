import os
import random

class SMBIOS:
    def __init__(self):
        pass

    def generate_random_mac(self):
        # Generates a random MAC address
        return "".join([random.choice("0123456789ABCDEF") for x in range(12)])
