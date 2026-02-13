import http.server
import socketserver
import os
import argparse

# Parse arguments
parser = argparse.ArgumentParser(description="Serve the current directory")
parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
parser.add_argument("--dir", default=".", help="Directory to serve")
args = parser.parse_args()

os.chdir(args.dir)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=".", **kwargs)

if __name__ == "__main__":
    with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
        print(f"Serving {args.dir} at http://{args.host}:{args.port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
