# Add Python DLL directory to PATH

from _winreg import *
import os
import sys

def install():

    dll_path = os.path.join(sys.prefix, 'DLLs')
    try:
        path = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
        reg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        key = OpenKey(reg, path, 0, KEY_ALL_ACCESS)

        current_path, type_id = QueryValueEx(key, "PATH")

        if not dll_path.upper() in current_path.upper().split(";"):
            new_path = current_path + ';' + dll_path
            SetValueEx(key, "PATH", 0, REG_EXPAND_SZ, new_path)

        CloseKey(key)
        CloseKey(reg)

    except WindowsError:
        path = r'Environment'
        reg = ConnectRegistry(None, HKEY_CURRENT_USER)
        key = OpenKey(reg, path, 0, KEY_ALL_ACCESS)

        try:
            current_path, type_id = QueryValueEx(key, "PATH")
            if not dll_path.upper() in current_path.upper().split(";"):
                new_path = current_path + ';' + dll_path
                SetValueEx(key, "PATH", 0, REG_EXPAND_SZ, new_path)

            CloseKey(key)
            CloseKey(reg)

        except WindowsError:

            CreateKey(HKEY_CURRENT_USER, path)
            SetValueEx(key, "PATH", 0, REG_EXPAND_SZ, dll_path)

            CloseKey(key)
            CloseKey(reg)

if __name__=='__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '-install':
        install()

