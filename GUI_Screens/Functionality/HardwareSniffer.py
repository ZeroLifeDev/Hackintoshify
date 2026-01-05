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
            self._detect_bios_mode()
        except Exception as e:
            print(f"Sniffer Error: {e}")
        
        return self.info

    def _detect_cpu(self):
        try:
            if cpuinfo:
                info = cpuinfo.get_cpu_info()
                # Try to get the raw brand string which contains "Model X" etc.
                model_name = info.get('brand_raw', '') or info.get('brand', '') or platform.processor()
            else:
                model_name = platform.processor()
                
            self.info['cpu_model'] = model_name
            
            # --- Detection Logic ---
            
            # 1. Parse "Family X Model Y" strings (common in some raw CPUID returns)
            # Example: "Intel(R) Core(TM) i5-4590 CPU @ 3.30GHz" vs "Intel64 Family 6 Model 63 Stepping 2"
            if "Family" in model_name and "Model" in model_name:
                try:
                    # Parse "Family 6 Model 63" -> Haswell
                    import re
                    m = re.search(r'Model\s+(\d+)', model_name)
                    if m:
                        model_id = int(m.group(1))
                        # Haswell: 60, 63, 69, 70
                        if model_id in [60, 63, 69, 70]:
                            self.info['cpu_family'] = "Intel Desktop (Haswell)"
                        # Ivy Bridge: 58
                        elif model_id == 58:
                            self.info['cpu_family'] = "Intel Desktop (Ivy Bridge)"
                        # Sandy Bridge: 42, 45
                        elif model_id in [42, 45]:
                            self.info['cpu_family'] = "Intel Desktop (Sandy Bridge)"
                        # Skylake: 94, 78, 85
                        elif model_id in [94, 78, 85]:
                             self.info['cpu_family'] = "Intel Desktop (Skylake)"
                except: pass

            # 2. Map based on Model Name String (e.g. "i7-8700K")
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

            # 3. Regex Fallback for "iX-XXXX" or "Xeon" if still unknown
            if self.info['cpu_family'] == "Unknown":
                # Check for Xeon specifically
                if "XEON" in model_name.upper():
                    # Xeon v3 = Haswell, v4 = Broadwell, v2 = Ivy Bridge, No 'v' = Sandy Bridge (mostly)
                    if " v3" in model_name: self.info['cpu_family'] = "Intel Desktop (Haswell)"
                    elif " v4" in model_name: self.info['cpu_family'] = "Intel Desktop (Broadwell)"
                    elif " v2" in model_name: self.info['cpu_family'] = "Intel Desktop (Ivy Bridge)"
                    elif " v5" in model_name: self.info['cpu_family'] = "Intel Desktop (Skylake)"
                    else: self.info['cpu_family'] = "Intel Desktop (Sandy Bridge)" # Default for older Xeons
                else:
                    self.info['cpu_family'] = self._map_cpu_generation(model_name)
                
        except Exception as e:
            print(f"CPU Detect Error: {e}")
            self.info['cpu_model'] = f"Error: {str(e)}"

    def _map_cpu_generation(self, name):
        if not name: return "Unknown"
        name = name.upper()
        
        # Intel Core iX-XXXX
        match = re.search(r'I\d-(\d{4,5})', name)
        if match:
            try:
                model_num = int(match.group(1))
                # Get generation (first digit if 4 digits, first 2 if 5 digits)
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
                if gen == 10: return "Intel Desktop (Comet Lake)"
                if gen == 11: return "Intel Desktop (Rocket Lake)"
                if gen == 12: return "Intel Desktop (Alder Lake)"
                if gen >= 13: return "Intel Desktop (Raptor Lake)"
            except: pass
            
        return "Unknown"

    def _detect_gpu(self):
        try:
            c = wmi.WMI()
            found_gpus = []
            for gpu in c.Win32_VideoController():
                name = gpu.Name
                if not name: continue
                # Filter junk
                if any(x in name.upper() for x in ["MIRROR", "DAMEWARE", "RDP", "VNC", "REMOTE", "MICROSOFT BASIC"]):
                    continue
                found_gpus.append(name)
            
            if found_gpus:
                self.info['gpu_model'] = found_gpus[0]
                # Try to prefer discrete
                for g in found_gpus:
                    if "NVIDIA" in g.upper() or "AMD" in g.upper() or "RADEON" in g.upper():
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
        try:
            c = wmi.WMI()
            for nic in c.Win32_NetworkAdapter(PhysicalAdapter=True):
                name = nic.Name.upper()
                if "WIFI" in name or "WIRELESS" in name or "802.11" in name:
                    self.info['has_wifi'] = True
                elif "ETHERNET" in name or "GIGABIT" in name or "CONTROLLER" in name:
                     if "REALTEK" in name: self.info['ethernet'] = "RealtekRTL8111"
                     elif "INTEL" in name: self.info['ethernet'] = "IntelMausi"
                     elif "ATHEROS" in name: self.info['ethernet'] = "AtherosE2200"
        except: pass

    def _detect_bios_mode(self):
        # On Windows, we can check setupapi or systeminfo
        # A simple check is checking if secure boot dict exists or using wmi
        try:
            c = wmi.WMI()
            # Win32_ComputerSystem -> Model
            # This is hard to detect perfectly from python without admin rights sometimes
            # But usually newer PCs are UEFI.
            # Let's rely on user or default true.
            pass
        except:
            pass
