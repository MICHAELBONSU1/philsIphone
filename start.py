import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Change to backend directory
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

# Add venv to path
venv_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'venv', 'Lib')
sys.path.insert(0, venv_lib)

# Run the Flask app
from app import app

if __name__ == '__main__':
    print("Starting Phil's iPhone server...")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, host='127.0.0.1', port=5000)
