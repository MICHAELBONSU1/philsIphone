import subprocess
import sys
import os

# Install dependencies first
print("Installing dependencies...")
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask', 'werkzeug', 'flask-sqlalchemy'])
print("Dependencies installed.\n")

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(project_root, 'backend')

# Add backend to path
sys.path.insert(0, backend_dir)

# Change to backend directory
os.chdir(backend_dir)

# Import and run the Flask app
from app import app

print("=" * 50)
print("Phil's iPhone Server Starting...")
print("=" * 50)
print("\nOpen http://127.0.0.1:5000 in your browser\n")
print("Admin Login:")
print("  Username: phil")
print("  Password: admin123")
print("=" * 50)

app.run(debug=True, host='127.0.0.1', port=5000)
