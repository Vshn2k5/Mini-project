
import os
import re

frontend_dir = r"h:\HEALTH-BITE_FINAL-!!!!!!!!!!!\HEALTH-BITE_FINAL-main\frontend"

replacements = {
    r"window\.location\.href\s*=\s*'(\.\./)*index\.html'": "window.location.href = '/index.html'",
    r'window\.location\.href\s*=\s*"(\.\./)*index\.html"': 'window.location.href = "/index.html"',
    
    r"window\.location\.href\s*=\s*'(\.\./)*health\.html'": "window.location.href = '/health.html'",
    r'window\.location\.href\s*=\s*"(\.\./)*health\.html"': 'window.location.href = "/health.html"',
    
    r"window\.location\.href\s*=\s*'(\.\./)*user\.html'": "window.location.href = '/user.html'",
    r'window\.location\.href\s*=\s*"(\.\./)*user\.html"': 'window.location.href = "/user.html"',
    
    r"window\.location\.href\s*=\s*'(\.\./)*admin\.html'": "window.location.href = '/admin.html'",
    r'window\.location\.href\s*=\s*"(\.\./)*admin\.html"': 'window.location.href = "/admin.html"',
    
    r"window\.location\.href\s*=\s*'(\.\./)*cart\.html'": "window.location.href = '/cart.html'",
    r'window\.location\.href\s*=\s*"(\.\./)*cart\.html"': 'window.location.href = "/cart.html"',
    
    r"window\.location\.href\s*=\s*'(\.\./)*payment\.html'": "window.location.href = '/payment.html'",
    r'window\.location\.href\s*=\s*"(\.\./)*payment\.html"': 'window.location.href = "/payment.html"',
    
    r"window\.location\.href\s*=\s*'(\.\./)*orders\.html(\?success=1)?'": "window.location.href = '/orders.html\\2'",
    r'window\.location\.href\s*=\s*"(\.\./)*orders\.html(\?success=1)?"': 'window.location.href = "/orders.html\\2"',
    
    r"window\.location\.href\s*=\s*'(\.\./)*health-assistant\.html'": "window.location.href = '/health-assistant.html'",
    r'window\.location\.href\s*=\s*"(\.\./)*health-assistant\.html"': 'window.location.href = "/health-assistant.html"',
    
    r"window\.location\.href\s*=\s*'(\.\./)*admin-inventory\.html'": "window.location.href = '/admin/pages/admin-inventory.html'",
    r'window\.location\.href\s*=\s*"(\.\./)*admin-inventory\.html"': 'window.location.href = "/admin/pages/admin-inventory.html"',
}

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
        
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed redirects in: {filepath}")

for root, _, files in os.walk(frontend_dir):
    for filename in files:
        if filename.endswith(".html") or filename.endswith(".js"):
            filepath = os.path.join(root, filename)
            fix_file(filepath)

print("Done.")
