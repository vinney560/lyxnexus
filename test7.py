import os
import re
filename = "file1_@-B.py"

def short_filename(filename, length=4):
    file, ext = os.path.splitext(filename)
    name = re.sub(r'\W', '', file)
    return f"{name}&I_Love_Coding{ext}" if len(name) > length else f"{name}@LN{ext}"

print(short_filename(filename))