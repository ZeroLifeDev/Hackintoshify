import sys
import os
import shutil
import binascii
import zipfile
import tempfile
import getpass
import re

class DSDT:
    def __init__(self, **kwargs):
        self.r = kwargs.get("run", None)
        self.u = kwargs.get("utils", None)
        self.acpi_tables = {}
        # Compiling Regex for Hex matching
        self.hex_match = re.compile(r"^[0-9A-F]+$")

    def load(self, path):
        # Placeholder for full load logic if needed
        # We assume path is a file or dir
        return (True, [])

    def get_dsdt_or_only(self):
        # Return DSDT if exists, or if only 1 table, return that
        dsdt = self.get_table_with_signature("DSDT")
        if dsdt: return dsdt
        if len(self.acpi_tables) == 1:
            return list(self.acpi_tables.values())[0]
        return None

    def check_output(self, output):
        t_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), output)
        if not os.path.isdir(t_folder):
            os.makedirs(t_folder)
        return t_folder

    def get_hex_from_int(self, total, pad_to = 4):
        hex_str = hex(total)[2:].upper().rjust(pad_to,"0")
        return "".join([hex_str[i:i + 2] for i in range(0, len(hex_str), 2)][::-1])

    def get_hex(self, line):
        # strip the header and commented end
        return line.split(":")[1].split("//")[0].replace(" ","")

    def get_line(self, line):
        # Strip the header and commented end - no space replacing though
        line = line.split("//")[0]
        if ":" in line:
            return line.split(":")[1]
        return line

    def get_hex_bytes(self, line):
        return binascii.unhexlify(line)

    def get_str_bytes(self, value):
        if sys.version_info >= (3,0) and isinstance(value,str):
            value = value.encode()
        return value

    def get_table_with_id(self, table_id):
        table_id = self.get_str_bytes(table_id)
        return next((v for k,v in self.acpi_tables.items() if table_id == v.get("id")),None)

    def get_table_with_signature(self, table_sig):
        table_sig = self.get_str_bytes(table_sig)
        return next((v for k,v in self.acpi_tables.items() if table_sig == v.get("signature")),None)

    def get_table(self, table_id_or_sig):
        table_id_or_sig = self.get_str_bytes(table_id_or_sig)
        return next((v for k,v in self.acpi_tables.items() if table_id_or_sig in (v.get("signature"),v.get("id"))),None)

    def get_dsdt(self):
        return self.get_table_with_signature("DSDT")

    def find_previous_hex(self, index=0, table=None):
        if not table: table = self.get_dsdt_or_only()
        if not table: return ("",-1,-1)
        start_index = -1
        end_index   = -1
        old_hex = True
        for i,line in enumerate(table.get("lines","")[index::-1]):
            if old_hex:
                if not self.is_hex(line):
                    old_hex = False
                continue
            if self.is_hex(line):
                end_index = index-i
                hex_text,start_index = self.get_hex_ending_at(end_index,table=table)
                return (hex_text, start_index, end_index)
        return ("",start_index,end_index)

    def find_next_hex(self, index=0, table=None):
        if not table: table = self.get_dsdt_or_only()
        if not table: return ("",-1,-1)
        start_index = -1
        end_index   = -1
        old_hex = True
        for i,line in enumerate(table.get("lines","")[index:]):
            if old_hex:
                if not self.is_hex(line):
                    old_hex = False
                continue
            if self.is_hex(line):
                start_index = i+index
                hex_text,end_index = self.get_hex_starting_at(start_index,table=table)
                return (hex_text, start_index, end_index)
        return ("",start_index,end_index)

    def is_hex(self, line):
        return self.hex_match.match(line) is not None if hasattr(self, 'hex_match') else False

    def get_hex_starting_at(self, start_index, table=None):
        if not table: table = self.get_dsdt_or_only()
        if not table: return ("",-1)
        hex_text = ""
        index = -1
        for i,x in enumerate(table.get("lines","")[start_index:]):
            if not self.is_hex(x):
                break
            hex_text += self.get_hex(x)
            index = i+start_index
        return (hex_text, index)

    def get_hex_ending_at(self, start_index, table=None):
        if not table: table = self.get_dsdt_or_only()
        if not table: return ("",-1)
        hex_text = ""
        index = -1
        for i,x in enumerate(table.get("lines","")[start_index::-1]):
            if not self.is_hex(x):
                break
            hex_text = self.get_hex(x)+hex_text
            index = start_index-i
        return (hex_text, index)

    def get_shortest_unique_pad(self, current_hex, index, instance=0, table=None):
        if not table: table = self.get_dsdt_or_only()
        if not table: return None
        try:    left_pad  = self.get_unique_pad(current_hex, index, False, instance, table=table)
        except: left_pad  = None
        try:    right_pad = self.get_unique_pad(current_hex, index, True, instance, table=table)
        except: right_pad = None
        try:    mid_pad   = self.get_unique_pad(current_hex, index, None, instance, table=table)
        except: mid_pad   = None
        if left_pad == right_pad == mid_pad is None: raise Exception("No unique pad found!")
        min_pad = None
        for x in (left_pad,right_pad,mid_pad):
            if x is None: continue
            if min_pad is None or len(x[0]+x[1]) < len(min_pad[0]+min_pad[1]):
                min_pad = x
        return min_pad

    def get_unique_pad(self, current_hex, index, direction=None, instance=0, table=None):
        if not table: table = self.get_dsdt_or_only()
        if not table: raise Exception("No valid table passed!")
        start_index = index
        line,last_index = self.get_hex_starting_at(index,table=table)
        if last_index == -1:
            raise Exception("Could not find hex starting at index {}!".format(index))
        first_line = line
        while True:
            if current_hex in line or len(line) >= len(first_line)+len(current_hex):
                break
            new_line,_index,last_index = self.find_next_hex(last_index, table=table)
            if last_index == -1:
                raise Exception("Hit end of file before passed hex was located!")
            line += new_line
        if not current_hex in line:
            raise Exception("{} not found in table at index {}-{}!".format(current_hex,start_index,last_index))
        padl = padr = ""
        parts = line.split(current_hex)
        if instance >= len(parts)-1:
            raise Exception("Instance out of range!")
        linel = current_hex.join(parts[0:instance+1])
        liner = current_hex.join(parts[instance+1:])
        while True:
            check_bytes = self.get_hex_bytes(padl+current_hex+padr)
            if table.get("raw", b"").count(check_bytes) == 1:
                break
            if direction == True or (direction is None and len(padr)<=len(padl)):
                if not len(liner):
                    liner, _index, last_index = self.find_next_hex(last_index, table=table)
                    if last_index == -1: raise Exception("Hit end of file before unique hex was found!")
                padr  = padr+liner[0:2]
                liner = liner[2:]
                continue
            if direction == False or (direction is None and len(padl)<=len(padr)):
                if not len(linel):
                    linel, start_index, _index = self.find_previous_hex(start_index, table=table)
                    if _index == -1: raise Exception("Hit end of file before unique hex was found!")
                padl  = linel[-2:]+padl
                linel = linel[:-2]
                continue
            break
        return (padl,padr)

    def get_scope(self,starting_index=0,add_hex=False,strip_comments=False,table=None):
        if not table: table = self.get_dsdt_or_only()
        if not table: return []
        brackets = None
        scope = []
        for line in table.get("lines","")[starting_index:]:
            if self.is_hex(line):
                if add_hex:
                    scope.append(line)
                continue
            line = self.get_line(line) if strip_comments else line
            scope.append(line)
            if brackets is None:
                if line.count("{"):
                    brackets = line.count("{")
                continue
            brackets = brackets + line.count("{") - line.count("}")
            if brackets <= 0:
                return scope
        return scope
        
    def get_device_paths(self, obj="HPET",table=None):
        # Placeholder mapping
        # In real scenario, we need methods get_path_of_type which relies on complex parsing
        # I am adding stub methods to make the app run based on user input for now
        return []

    def get_device_paths_with_hid(self,hid="ACPI000E",table=None):
        return []

    def get_method_paths(self, obj="_STA",table=None):
        return []

    def get_name_paths(self, obj="CPU0",table=None):
        return []
    
    def get_processor_paths(self, obj_type="Processor",table=None):
        return []
        
    def get_path_of_type(self, obj_type="Device", obj="HPET", table=None):
        return []
