import sys
sys.path.insert(0, 'backend')
from app import app

with app.test_client() as client:
    response = client.get('/home')
    html = response.data.decode('utf-8')
    
    # Find the loadNews function content
    start = html.find('async function loadNews()')
    if start >= 0:
        end = html.find('}', start)
        # Find the matching closing brace
        brace_count = 1
        i = end + 1
        while brace_count > 0 and i < len(html):
            if html[i] == '{':
                brace_count += 1
            elif html[i] == '}':
                brace_count -= 1
            i += 1
        print("loadNews function found, length:", i - start)
        print("First 500 chars:")
        print(html[start:start+500])
    else:
        print("loadNews function NOT found")