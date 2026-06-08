import sys
sys.path.insert(0, 'backend')
from app import app

with app.test_client() as client:
    response = client.get('/home')
    html = response.data.decode('utf-8')
    
    # Check for JavaScript errors
    print("Checking for potential JS template issues...")
    
    # Check if template variables were replaced
    if "{{ session.get" in html:
        print("ERROR: Template variable not replaced!")
    else:
        print("Template variables replaced correctly")
    
    # Check for backticks in JavaScript
    if "`" in html:
        print("Template literals (backticks) found in JS")
    
    # Print last 100 chars before </script>
    script_end = html.rfind('</script>')
    if script_end >= 0:
        print("Last 200 chars before </script>:")
        print(html[script_end-200:script_end])