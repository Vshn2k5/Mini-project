import os
import glob

dirs = ["seeders", "tools", "scripts", "tests"]
base = os.path.dirname(os.path.abspath(__file__))

prepend_code = """import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""

for d in dirs:
    path = os.path.join(base, d, "*.py")
    for f in glob.glob(path):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Use 'import sqlite3' or 'from database ' or 'from models '
            needs_fix = ("from database" in content or "from models" in content or "from ai_engine" in content)
            
            if "sys.path.append" not in content and needs_fix:
                with open(f, 'w', encoding='utf-8') as file:
                    file.write(prepend_code + content)
                print(f"Fixed {os.path.basename(f)}")
        except Exception as e:
            print(f"Error on {f}: {e}")
