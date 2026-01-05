import os
import requests
import zipfile
import shutil
import time
from PySide6.QtCore import QObject, Signal, QThread

# Hardcoded versions for stability (can be updated or made dynamic later)
OPENCORE_URL = "https://github.com/acidanthera/OpenCorePkg/releases/download/0.9.6/OpenCore-0.9.6-RELEASE.zip"
KEXTS = {
    "Lilu": "https://github.com/acidanthera/Lilu/releases/download/1.6.7/Lilu-1.6.7-RELEASE.zip",
    "VirtualSMC": "https://github.com/acidanthera/VirtualSMC/releases/download/1.3.2/VirtualSMC-1.3.2-RELEASE.zip",
    "WhateverGreen": "https://github.com/acidanthera/WhateverGreen/releases/download/1.6.6/WhateverGreen-1.6.6-RELEASE.zip",
    "AppleALC": "https://github.com/acidanthera/AppleALC/releases/download/1.8.7/AppleALC-1.8.7-RELEASE.zip"
}

class EFIBuilderWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, output_path, cpu_family, is_uefi):
        super().__init__()
        self.output_path = output_path
        self.cpu_family = cpu_family
        self.is_uefi = is_uefi
        self.temp_dir = os.path.join(output_path, "temp_efi_build")

    def run(self):
        try:
            self.progress.emit(0, "Starting EFI Build...")
            
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)

            # 1. Download OpenCore
            self.progress.emit(10, "Downloading OpenCore...")
            oc_zip = self.download_file(OPENCORE_URL, "OpenCore.zip")
            
            # 2. Extract OpenCore
            self.progress.emit(20, "Extracting OpenCore...")
            self.extract_opencore(oc_zip)

            # 3. Download and Install Kexts
            total_kexts = len(KEXTS)
            for idx, (name, url) in enumerate(KEXTS.items()):
                pct = 30 + int((idx / total_kexts) * 40) # 30% to 70%
                self.progress.emit(pct, f"Installing {name}...")
                kzip = self.download_file(url, f"{name}.zip")
                self.extract_kext(kzip, name)

            # 4. Finalize Structure (UEFI vs Legacy Drivers)
            self.progress.emit(80, "Configuring Drivers & Tools...")
            self.configure_drivers()

            # 5. Cleanup
            self.progress.emit(90, "Cleaning up...")
            self.cleanup()

            self.progress.emit(100, "EFI Creation Complete!")
            self.finished.emit(os.path.join(self.output_path, "EFI"))

        except Exception as e:
            self.error.emit(str(e))
            # Cleanup on error?
            
    def download_file(self, url, name):
        dest = os.path.join(self.temp_dir, name)
        # Increased timeout to 60 seconds to handle slow Github connections
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest

    def extract_opencore(self, zip_path):
        # ... (Existing extraction logic, but we need Sample.plist too)
        extract_path = os.path.join(self.temp_dir, "OC_Ext")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Move EFI folder
        source_efi = os.path.join(extract_path, "X64", "EFI")
        dest_efi = os.path.join(self.output_path, "EFI")
        
        if os.path.exists(dest_efi):
            shutil.rmtree(dest_efi)
        shutil.copytree(source_efi, dest_efi)
        
        # Copy Sample.plist -> config.plist
        # Usually in Docs/Sample.plist
        source_sample = os.path.join(extract_path, "Docs", "Sample.plist")
        dest_config = os.path.join(dest_efi, "OC", "config.plist")
        
        if os.path.exists(source_sample):
            shutil.copy(source_sample, dest_config)
            self.configure_plist(dest_config)
        else:
            self.error.emit("Sample.plist not found in OpenCore package!")

    def configure_plist(self, plist_path):
        import plistlib
        
        try:
            with open(plist_path, 'rb') as f:
                plist = plistlib.load(f)
            
            # --- 1. PlatformInfo (SMBIOS) ---
            # Simplified mapping
            model = "iMac19,1" # Default Coffee Lake
            if "Haswell" in self.cpu_family: model = "iMac14,4"
            elif "Ivy Bridge" in self.cpu_family: model = "iMac13,2"
            elif "Sandy Bridge" in self.cpu_family: model = "iMac12,2"
            elif "Skylake" in self.cpu_family: model = "iMac17,1"
            elif "Kaby Lake" in self.cpu_family: model = "iMac18,1"
            elif "Comet Lake" in self.cpu_family: model = "iMac20,1"
            elif "Ryzen" in self.cpu_family: model = "iMacPro1,1" # Standard for AMD
            
            plist['PlatformInfo']['Generic']['SystemProductName'] = model
            
            # --- 2. ACPI Quirks ---
            # Basic defaults for stability
            
            # --- 3. Booter Quirks ---
            if "Haswell" in self.cpu_family or "Ivy" in self.cpu_family:
                # Legacy / Older
                plist['Booter']['Quirks']['AvoidRuntimeDefrag'] = True
                plist['Booter']['Quirks']['SetupVirtualMap'] = True
            
            # --- 4. UEFI / Legacy Drivers ---
            # If Legacy, OpenCanopy might fail without OpenDuet, revert to Text
            if not self.is_uefi:
                 plist['UEFI']['Output']['ConsoleMode'] = "Max"
            
            # --- 5. Add Kexts to Config ---
            # We must scan our downloaded kexts and add them to Kernel->Add
            # We downloaded them to EFI/OC/Kexts
            kexts_dir = os.path.join(self.output_path, "EFI", "OC", "Kexts")
            if os.path.exists(kexts_dir):
                kext_list = []
                # Priority: Lilu, VirtualSMC, WhateverGreen, AppleALC
                # Simple sort by priority list
                priority = ["Lilu.kext", "VirtualSMC.kext", "WhateverGreen.kext", "AppleALC.kext"]
                
                detected = [f for f in os.listdir(kexts_dir) if f.endswith(".kext")]
                
                # Add priority ones first
                for p in priority:
                    if p in detected:
                        kext_list.append(self._make_kext_entry(p))
                        detected.remove(p)
                
                # Add rest
                for d in detected:
                     kext_list.append(self._make_kext_entry(d))
                
                plist['Kernel']['Add'] = kext_list

            with open(plist_path, 'wb') as f:
                plistlib.dump(plist, f)
                
        except Exception as e:
            print(f"Plist Config Error: {e}")
            self.error.emit(f"Config Patcher failed: {e}")

    def _make_kext_entry(self, kext_name):
        # Basic entry structure for OC 0.9.x
        return {
            'Arch': 'x86_64',
            'BundlePath': kext_name,
            'Comment': '',
            'Enabled': True,
            'ExecutablePath': f'Contents/MacOS/{kext_name[:-5]}', # Strip .kext
            'MaxKernel': '',
            'MinKernel': '',
            'PlistPath': 'Contents/Info.plist'
        }


    def extract_kext(self, zip_path, kext_name):
        extract_path = os.path.join(self.temp_dir, f"Kext_{kext_name}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        # Find the .kext folder (usually in root or Release folder)
        kext_source = None
        for root, dirs, files in os.walk(extract_path):
            for d in dirs:
                if d.endswith(".kext"):
                    kext_source = os.path.join(root, d)
                    break
            if kext_source: break
            
        if kext_source:
             dest_kexts = os.path.join(self.output_path, "EFI", "OC", "Kexts")
             if not os.path.exists(dest_kexts): os.makedirs(dest_kexts)
             
             final_dest = os.path.join(dest_kexts, os.path.basename(kext_source))
             if os.path.exists(final_dest): shutil.rmtree(final_dest)
             shutil.copytree(kext_source, final_dest)

    def configure_drivers(self):
        drivers_path = os.path.join(self.output_path, "EFI", "OC", "Drivers")
        # Remove unused drivers to save space/cleanliness (Optional)
        # For Legacy vs UEFI, OpenCore handles most via config.plist, but we might need OpenDuet for legacy.
        # OpenDuet is usually in Utilities folder of OC package, which we didn't fully copy.
        # For now, we assume the default X64 EFI folder structure.
        
        # If Legacy, we ideally need to copy boot & generated boot loader files.
        # This basic builder focuses on populating the EFI/OC/Kexts structure first.
        pass

    def cleanup(self):
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass
