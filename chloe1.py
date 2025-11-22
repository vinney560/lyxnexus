import ctypes
import os, subprocess

FILENAME = 'chloe.c'
C_OUTPUT = './chloe.so'
def compiled_c():
    lib_name = C_OUTPUT
    cmd = f'gcc -shared -o {C_OUTPUT} -fPIC {FILENAME}'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("Complied!")
        return lib_name
    else:
        print("Error: ", result.stderr)
        return None
    
lib_name = compiled_c()
if lib_name:
    lib = ctypes.CDLL(lib_name)
    lib.Name.argtypes = []
    lib.Name.restype = ctypes.c_char_p
    name = lib.Name()
    print(f"Read this: {name.decode()}\n")

if __name__ == '__main__':
    compiled_c()