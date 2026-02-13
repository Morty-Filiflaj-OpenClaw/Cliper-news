import http.server
import socketserver
import os
import argparse
import json
import cgi

# Parse arguments
parser = argparse.ArgumentParser(description="Serve the current directory")
parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
parser.add_argument("--dir", default=".", help="Directory to serve")
args = parser.parse_args()

try:
    os.chdir(args.dir)
except FileNotFoundError:
    print(f"Directory {args.dir} not found. Running in current.")

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/save':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                filename = data.get('filename')
                content = data.get('content')
                
                if not filename or not content:
                    self.send_error(400, "Missing filename or content")
                    return

                # Security: prevent directory traversal
                filename = os.path.basename(filename)
                if not filename.endswith('.md'):
                    filename += '.md'
                    
                report_path = os.path.join("reports", filename)
                
                # Ensure reports dir exists
                os.makedirs("reports", exist_ok=True)
                
                with open(report_path, "w") as f:
                    f.write(content)
                    
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "file": report_path}).encode('utf-8'))
                
                # Re-generate index if generate.py exists
                if os.path.exists("generate.py"):
                    os.system("python3 generate.py")
                    
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not Found")

if __name__ == "__main__":
    # Allow address reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
        print(f"Serving {args.dir} at http://{args.host}:{args.port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
