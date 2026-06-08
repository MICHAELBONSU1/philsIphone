import sys
sys.path.insert(0, 'backend')
from app import app

with app.test_client() as client:
    response = client.get('/home')
    html = response.data.decode('utf-8')
    
    # Check if our news script is in the page
    if 'loadNews' in html:
        print("loadNews found in HTML")
        
        # Find all script tags
        import re
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"Found {len(scripts)} script blocks")
        
        for i, script in enumerate(scripts):
            if 'loadNews' in script:
                print(f"\nScript block {i} contains loadNews:")
                print(script[:800])
                break
    else:
        print("loadNews NOT found in HTML")