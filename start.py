import os
import sys
import socket

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

def get_lan_ip():
    """Get the local network IP address for easier mobile testing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_local_hostname():
    """Get the .local hostname for easier mDNS resolution on iPhone."""
    try:
        name = socket.gethostname()
        return f"{name}.local" if not name.endswith(".local") else name
    except Exception:
        return None

if __name__ == '__main__':
    preferred_port = os.environ.get('PORT')
    default_port = 5005
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    # Secure context (microphone access) requires HTTPS for non-localhost IP access
    use_https = os.environ.get('USE_HTTPS', '1') == '1'

    if preferred_port:
        try:
            preferred_port = int(preferred_port)
        except ValueError:
            preferred_port = default_port
    else:
        preferred_port = default_port

    app.debug = debug_mode

    print("Starting Phil's iPhone server...")
    print(f"Opening on the first available port starting at {preferred_port}...")
    if not os.environ.get('PORT'):
        print("Port 5000 will be tried last to avoid common macOS port conflicts.")

    if not use_https:
        print("\n" + "╔" + "═" * 58 + "╗")
        print("║" + " " * 21 + "SECURITY WARNING" + " " * 21 + "║")
        print("╠" + "═" * 58 + "╣")
        print("║  Server is running over HTTP (Insecure Context).         ║")
        print("║  Microphone access is DISABLED by browsers on non-local  ║")
        print("║  IP addresses (like your iPhone).                        ║")
        print("║                                                          ║")
        print("║  TO FIX: Restart with HTTPS enabled:                     ║")
        print("║  USE_HTTPS=1 python3 start.py                            ║")
        print("╚" + "═" * 58 + "╝\n")

    candidate_ports = [preferred_port]
    for fallback in (5005, 5001, 8000, 8080, 5000):
        if fallback not in candidate_ports:
            candidate_ports.append(fallback)

    protocol = "https" if use_https else "http"
    lan_ip = get_lan_ip()
    hostname = get_local_hostname()

    for port in candidate_ports:
        try:
            print(f"Trying to start server on port {port}...")
            print("=" * 60)
            print(f"  SERVER STARTED SUCCESSFULLY")
            print("-" * 60)
            print(f"  LOCAL: {protocol}://localhost:{port}")
            print(f"  IP:    {protocol}://{lan_ip}:{port}")
            if hostname:
                print(f"  HOST:  {protocol}://{hostname}:{port}")
            print("-" * 60)
            
            ssl_context = None
            if use_https:
                print("  SECURE CONTEXT ENABLED (Required for Microphone)")
                cert_path = os.path.join(project_root, 'cert.pem')
                key_path = os.path.join(project_root, 'key.pem')
                if os.path.exists(cert_path) and os.path.exists(key_path):
                    print("  Using trusted SSL certificate (mkcert). No warnings expected!")
                    ssl_context = (cert_path, key_path)
                else:
                    print("  IMPORTANT: You must type the full 'https://' prefix.")
                    print("  Your browser will show a warning: Click 'Advanced'")
                    print(f"  then 'Proceed to {lan_ip} (unsafe)'.")
                    ssl_context = 'adhoc'
            print("=" * 60)
            print("\nPress Ctrl+C to stop the server.")
            socketio.run(
                app,
                debug=debug_mode,
                use_reloader=False,
                host='0.0.0.0',
                port=port,
                allow_unsafe_werkzeug=True,
                ssl_context=ssl_context
            )
            break
        except OSError as exc:
            print(f"Port {port} unavailable: {exc}")
    else:
        raise SystemExit("No available port found. Set PORT to a free port and restart.")
