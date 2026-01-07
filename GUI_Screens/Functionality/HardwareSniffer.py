import platform
import re
try:
    import wmi
except ImportError:
    wmi = None

try:
    import cpuinfo
except ImportError:
    cpuinfo = None

class HardwareSniffer:
    def __init__(self):
        self.info = {
            "cpu_model": "Unknown",
            "cpu_family": "Unknown",
            "gpu_model": "Unknown",
            "gpu_vendor": "Unknown",
            "mobo_vendor": "Unknown",
            "mobo_model": "Unknown",
            "ethernet": "Unknown",
            "has_wifi": False,
            "is_uefi": True
        }

    def detect(self):
        try:
            self._detect_cpu()
            self._detect_gpu()
            self._detect_motherboard()
            self._detect_network()
            self._detect_input_devices()
            self._detect_bluetooth()
            self._detect_storage()
            self._detect_bios_mode()
        except Exception as e:
            print(f"Sniffer Error: {e}")
        
        return self.info

    # ... (CPU/GPU/Mobo methods remain mostly same, focusing on new additions) ...

    def _detect_cpu(self):
        try:
            if cpuinfo:
                info = cpuinfo.get_cpu_info()
                model_name = info.get('brand_raw', '') or info.get('brand', '') or platform.processor()
            else:
                model_name = platform.processor()
                
            self.info['cpu_model'] = model_name
            
            # 1. Parse "Family X Model Y" strings
            if "Family" in model_name and "Model" in model_name:
                try:
                    m = re.search(r'Model\s+(\d+)', model_name)
                    if m:
                        model_id = int(m.group(1))
                        if model_id in [60, 63, 69, 70]: self.info['cpu_family'] = "Intel Desktop (Haswell)"
                        elif model_id == 58: self.info['cpu_family'] = "Intel Desktop (Ivy Bridge)"
                        elif model_id in [42, 45]: self.info['cpu_family'] = "Intel Desktop (Sandy Bridge)"
                        elif model_id in [94, 78, 85]: self.info['cpu_family'] = "Intel Desktop (Skylake)"
                except: pass

            # 2. Map based on Model Name String
            if self.info['cpu_family'] == "Unknown" and model_name:
                if "Haswell" in model_name: self.info['cpu_family'] = "Intel Desktop (Haswell)"
                elif "Broadwell" in model_name: self.info['cpu_family'] = "Intel Desktop (Broadwell)"
                elif "Skylake" in model_name: self.info['cpu_family'] = "Intel Desktop (Skylake)"
                elif "Kaby Lake" in model_name: self.info['cpu_family'] = "Intel Desktop (Kaby Lake)"
                elif "Coffee Lake" in model_name: self.info['cpu_family'] = "Intel Desktop (Coffee Lake)"
                elif "Comet Lake" in model_name: self.info['cpu_family'] = "Intel Desktop (Comet Lake)"
                elif "Rocket Lake" in model_name: self.info['cpu_family'] = "Intel Desktop (Rocket Lake)"
                elif "Alder Lake" in model_name: self.info['cpu_family'] = "Intel Desktop (Alder Lake)"
                elif "Raptor Lake" in model_name: self.info['cpu_family'] = "Intel Desktop (Raptor Lake)"
                elif "Ryzen" in model_name: self.info['cpu_family'] = "AMD Ryzen (Zen/Zen2/Zen3)"
                elif "FX" in model_name or "Athlon" in model_name: self.info['cpu_family'] = "AMD FX/Athlon (Legacy)"

            # 3. Regex Fallback
            if self.info['cpu_family'] == "Unknown":
                if "XEON" in model_name.upper():
                    if " v3" in model_name: self.info['cpu_family'] = "Intel Desktop (Haswell)"
                    elif " v4" in model_name: self.info['cpu_family'] = "Intel Desktop (Broadwell)"
                    elif " v2" in model_name: self.info['cpu_family'] = "Intel Desktop (Ivy Bridge)"
                    elif " v5" in model_name: self.info['cpu_family'] = "Intel Desktop (Skylake)"
                    else: self.info['cpu_family'] = "Intel Desktop (Sandy Bridge)"
                else:
                    self.info['cpu_family'] = self._map_cpu_generation(model_name)
                
        except Exception as e:
            self.info['cpu_model'] = f"Error: {str(e)}"

    def _map_cpu_generation(self, name):
        if not name: return "Unknown"
        name = name.upper()
        match = re.search(r'I\d-(\d{4,5})', name)
        if match:
            try:
                model_num = int(match.group(1))
                gen_str = str(model_num)
                if len(gen_str) == 4: gen = int(gen_str[0])
                else: gen = int(gen_str[:2])
                
                if gen == 2: return "Intel Desktop (Sandy Bridge)"
                if gen == 3: return "Intel Desktop (Ivy Bridge)"
                if gen == 4: return "Intel Desktop (Haswell)"
                if gen == 5: return "Intel Desktop (Broadwell)"
                if gen == 6: return "Intel Desktop (Skylake)"
                if gen == 7: return "Intel Desktop (Kaby Lake)"
                if gen in [8, 9]: return "Intel Desktop (Coffee Lake)"
                if gen >= 10: return "Intel Desktop (Comet Lake)" # Simplified for newer
            except: pass
        return "Unknown"

    def _detect_gpu(self):
        try:
            c = wmi.WMI()
            found_gpus = []
            for gpu in c.Win32_VideoController():
                name = gpu.Name
                if not name: continue
                if any(x in name.upper() for x in ["MIRROR", "DAMEWARE", "RDP", "VNC", "REMOTE", "MICROSOFT BASIC"]):
                    continue
                found_gpus.append(name)
            
            if found_gpus:
                self.info['gpu_model'] = found_gpus[0]
                # Prefer discrete
                for g in found_gpus:
                    if any(v in g.upper() for v in ["NVIDIA", "AMD", "RADEON", "GTX", "RTX"]):
                        self.info['gpu_model'] = g
                        break
            
            gpu_name = self.info['gpu_model'].upper()
            if "NVIDIA" in gpu_name: self.info['gpu_vendor'] = "NVIDIA"
            elif "AMD" in gpu_name or "RADEON" in gpu_name: self.info['gpu_vendor'] = "AMD"
            elif "INTEL" in gpu_name: self.info['gpu_vendor'] = "INTEL"
        except: pass

    def _detect_motherboard(self):
        try:
            c = wmi.WMI()
            for board in c.Win32_BaseBoard():
                self.info['mobo_vendor'] = board.Manufacturer
                self.info['mobo_model'] = board.Product
        except: pass

    def _detect_network(self):
        self.info['wifi_model'] = "Not Detected"
        self.info['ethernet_model'] = "Not Detected"
        try:
            c = wmi.WMI()
            for nic in c.Win32_NetworkAdapter(PhysicalAdapter=True):
                name = nic.Name
                if not name: continue
                name_upper = name.upper()
                
                if "WIFI" in name_upper or "WIRELESS" in name_upper or "802.11" in name_upper or "WI-FI" in name_upper:
                    self.info['has_wifi'] = True
                    self.info['wifi_model'] = name
                elif "ETHERNET" in name_upper or "GIGABIT" in name_upper or "CONTROLLER" in name_upper:
                     self.info['ethernet_model'] = name # Capture full name
                     if "REALTEK" in name_upper: self.info['ethernet'] = "RealtekRTL8111"
                     elif "INTEL" in name_upper: self.info['ethernet'] = "IntelMausi"
                     elif "ATHEROS" in name_upper: self.info['ethernet'] = "AtherosE2200"
                     elif "BROADCOM" in name_upper: self.info['ethernet'] = "Broadcom"
        except: pass

    def _detect_bluetooth(self):
        self.info['has_bt'] = False
        self.info['bt_model'] = "Not Detected"
        try:
            c = wmi.WMI()
            # Win32_PnPEntity is slow to iterate entirely, so filtering is key. 
            # WMI query is safer than python-side filter for performance
            for dev in c.query("SELECT * FROM Win32_PnPEntity WHERE Name LIKE '%Bluetooth%' OR Caption LIKE '%Bluetooth%'"):
                name = dev.Name or dev.Caption
                # Ignore Microsoft generic enumerators
                if "ENUMERATOR" in name.upper() or "LE " in name.upper(): continue
                self.info['has_bt'] = True
                self.info['bt_model'] = name
                break
        except: pass

    def _detect_input_devices(self):
        self.info['keyboard_type'] = "USB/External"
        self.info['mouse_type'] = "USB/External"
        self.info['has_trackpad'] = False
        
        try:
            c = wmi.WMI()
            # Keyboards
            for kb in c.Win32_Keyboard():
                desc = kb.Description.upper()
                if "PS/2" in desc or "STANDARD 101/102-KEY" in desc:
                    self.info['keyboard_type'] = "PS/2 (Built-in)"
            
            # Pointing Devices
            for mouse in c.Win32_PointingDevice():
                desc = str(mouse.Description).upper() if mouse.Description else ""
                hw_type = str(mouse.HardwareType).upper() if mouse.HardwareType else ""
                
                if "TOUCHPAD" in desc or "TOUCHPAD" in hw_type or "SYNAPTICS" in desc or "ELAN" in desc:
                    self.info['has_trackpad'] = True
                    self.info['mouse_type'] = "Trackpad (I2C/PS2)"
                elif "PS/2" in desc:
                    self.info['mouse_type'] = "PS/2 Mouse"
        except: pass

    def _detect_storage(self):
        self.info['storage'] = []
        try:
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                model = disk.Model
                size_gb = int(int(disk.Size) / (1024**3)) if disk.Size else 0
                media_type = disk.MediaType if hasattr(disk, 'MediaType') else "Unknown"
                self.info['storage'].append(f"{model} ({size_gb} GB)")
        except: pass

    def _detect_bios_mode(self):
        self.info['bios_mode'] = "Unknown"
        try:
            # Requires Admin usually
            pass
        except: pass
