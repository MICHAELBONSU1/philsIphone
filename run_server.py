import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(project_root, 'backend')

sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

try:
    from app import app, socketio
except ModuleNotFoundError as exc:
    print("Failed to import the Flask app. Make sure you are running this script from the project root and have installed dependencies in your environment.")
    print("Try: .venv/bin/python3 -m pip install -r requirements.txt")
    raise

if __name__ == '__main__':
    preferred_port = os.environ.get('PORT')
    default_port = 5000
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    use_https = os.environ.get('USE_HTTPS', '0') == '1'

    if preferred_port:
        try:
            preferred_port = int(preferred_port)
        except ValueError:
            preferred_port = default_port
    else:
        preferred_port = default_port

    app.debug = debug_mode

    print("=" * 50)
    print("Phil's iPhone Server Starting...")
    print(f"Opening on port {preferred_port} only.")
    print("Admin Login:")
    print("  Username: phil")
    print("  Password: admin123")
    protocol = "https" if use_https else "http"
    print("=" * 50)

    candidate_ports = [preferred_port]

    for port in candidate_ports:
        try:
            print(f"Trying to start server on port {port}...")
            print(f"Server available at: {protocol}://127.0.0.1:{port}")
            print("Press Ctrl+C to stop the server.")
            socketio.run(
                app,
                debug=debug_mode,
                use_reloader=False,
                host='127.0.0.1',
                port=port,
                allow_unsafe_werkzeug=True,
                ssl_context='adhoc' if use_https else None
            )
            break
        except OSError as exc:
            print(f"Port {port} unavailable: {exc}")
    else:
        raise SystemExit("No available port found. Set PORT to a free port and restart.")
