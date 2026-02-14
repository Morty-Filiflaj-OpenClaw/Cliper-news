import http.server
import socketserver
import os
import argparse
import json
import cgi
import sqlite3
from datetime import datetime
from urllib.parse import parse_qs, urlparse

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

DB_FILE = "cliper.db"

def init_db():
    """Initialize SQLite database for categories, comments, and article versions"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Categories table
    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  slug TEXT UNIQUE NOT NULL,
                  created_at TEXT)''')
    
    # Comments table
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  article_slug TEXT NOT NULL,
                  author TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TEXT)''')
    
    # Article versions (history)
    c.execute('''CREATE TABLE IF NOT EXISTS article_versions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  article_slug TEXT NOT NULL,
                  content TEXT NOT NULL,
                  version INTEGER,
                  created_at TEXT)''')
    
    # Article metadata (categories, images)
    c.execute('''CREATE TABLE IF NOT EXISTS article_metadata
                 (article_slug TEXT PRIMARY KEY,
                  category_id INTEGER,
                  featured_image TEXT,
                  updated_at TEXT,
                  FOREIGN KEY(category_id) REFERENCES categories(id))''')
    
    conn.commit()
    conn.close()

init_db()

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/save':
            self._handle_save_article()
        elif self.path == '/api/categories':
            self._handle_create_category()
        elif self.path == '/api/comments':
            self._handle_create_comment()
        elif self.path == '/api/upload':
            self._handle_upload_image()
        else:
            self.send_error(404, "Not Found")
    
    def do_GET(self):
        if self.path == '/api/categories':
            self._handle_get_categories()
        elif self.path.startswith('/api/comments/'):
            article_slug = self.path.split('/')[-1]
            self._handle_get_comments(article_slug)
        elif self.path.startswith('/api/versions/'):
            article_slug = self.path.split('/')[-1]
            self._handle_get_versions(article_slug)
        elif self.path.startswith('/api/related/'):
            article_slug = self.path.split('/')[-1]
            self._handle_get_related(article_slug)
        elif self.path.startswith('/api/search'):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query).get('q', [''])[0]
            self._handle_search(query)
        else:
            # Serve static files
            super().do_GET()
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _handle_save_article(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            filename = data.get('filename')
            content = data.get('content')
            category_id = data.get('category_id')
            
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
            
            # Check if article exists (for versioning)
            slug = filename.replace('.md', '')
            if os.path.exists(report_path):
                # Save version history
                with open(report_path, 'r') as f:
                    old_content = f.read()
                self._save_version(slug, old_content)
            
            # Save new content
            with open(report_path, "w") as f:
                f.write(content)
            
            # Save metadata
            if category_id:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("""INSERT OR REPLACE INTO article_metadata (article_slug, category_id, updated_at)
                             VALUES (?, ?, ?)""", (slug, category_id, datetime.now().isoformat()))
                conn.commit()
                conn.close()
            
            self._send_json({"status": "success", "file": report_path})
            
            # Re-generate index if generate.py exists
            if os.path.exists("generate.py"):
                os.system("python3 generate.py")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def _save_version(self, slug, content):
        """Save article version to history"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Get current version count
        c.execute("SELECT COUNT(*) FROM article_versions WHERE article_slug = ?", (slug,))
        version = c.fetchone()[0] + 1
        
        c.execute("""INSERT INTO article_versions (article_slug, content, version, created_at)
                     VALUES (?, ?, ?, ?)""", (slug, content, version, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def _handle_create_category(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            name = data.get('name')
            if not name:
                self.send_error(400, "Missing category name")
                return
            
            import re
            slug = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO categories (name, slug, created_at) VALUES (?, ?, ?)",
                      (name, slug, datetime.now().isoformat()))
            cat_id = c.lastrowid
            conn.commit()
            conn.close()
            
            self._send_json({"id": cat_id, "name": name, "slug": slug})
        except Exception as e:
            self.send_error(500, str(e))
    
    def _handle_get_categories(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM categories ORDER BY name")
        rows = c.fetchall()
        conn.close()
        
        categories = [dict(row) for row in rows]
        self._send_json(categories)
    
    def _handle_create_comment(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            article_slug = data.get('article_slug')
            author = data.get('author', 'Anonymous')
            content = data.get('content')
            
            if not article_slug or not content:
                self.send_error(400, "Missing required fields")
                return
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""INSERT INTO comments (article_slug, author, content, created_at)
                         VALUES (?, ?, ?, ?)""",
                      (article_slug, author, content, datetime.now().isoformat()))
            comment_id = c.lastrowid
            conn.commit()
            conn.close()
            
            self._send_json({"id": comment_id, "status": "success"})
        except Exception as e:
            self.send_error(500, str(e))
    
    def _handle_get_comments(self, article_slug):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM comments WHERE article_slug = ? ORDER BY created_at DESC", (article_slug,))
        rows = c.fetchall()
        conn.close()
        
        comments = [dict(row) for row in rows]
        self._send_json(comments)
    
    def _handle_get_versions(self, article_slug):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, version, created_at FROM article_versions WHERE article_slug = ? ORDER BY version DESC", (article_slug,))
        rows = c.fetchall()
        conn.close()
        
        versions = [dict(row) for row in rows]
        self._send_json(versions)
    
    def _handle_get_related(self, article_slug):
        """Get related articles based on tags"""
        # Simple implementation: return recent articles (can be enhanced with tag matching)
        articles = []
        if os.path.exists("reports"):
            files = sorted([f for f in os.listdir("reports") if f.endswith('.md')], reverse=True)
            for f in files[:5]:
                if f.replace('.md', '') != article_slug:
                    articles.append({
                        "slug": f.replace('.md', ''),
                        "title": f.replace('.md', '').replace('-', ' ').title()
                    })
        
        self._send_json(articles[:3])
    
    def _handle_search(self, query):
        """Full-text search across articles"""
        results = []
        if not query or not os.path.exists("reports"):
            self._send_json(results)
            return
        
        query_lower = query.lower()
        files = [f for f in os.listdir("reports") if f.endswith('.md')]
        
        for f in files:
            try:
                with open(os.path.join("reports", f), 'r') as file:
                    content = file.read()
                    if query_lower in content.lower():
                        # Extract title from first line or filename
                        lines = content.split('\n')
                        title = f.replace('.md', '').replace('-', ' ').title()
                        for line in lines:
                            if line.startswith('# '):
                                title = line[2:]
                                break
                        
                        results.append({
                            "slug": f.replace('.md', ''),
                            "title": title,
                            "excerpt": content[:200] + "..."
                        })
            except Exception as e:
                print(f"Error reading {f}: {e}")
        
        self._send_json(results)
    
    def _handle_upload_image(self):
        """Handle image upload"""
        content_type = self.headers['Content-Type']
        if 'multipart/form-data' not in content_type:
            self.send_error(400, "Expected multipart/form-data")
            return
        
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            
            if 'image' not in form:
                self.send_error(400, "No image file")
                return
            
            file_item = form['image']
            if not file_item.file:
                self.send_error(400, "Empty file")
                return
            
            # Ensure uploads directory exists
            os.makedirs("uploads", exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{file_item.filename}"
            filepath = os.path.join("uploads", filename)
            
            # Save file
            with open(filepath, 'wb') as f:
                f.write(file_item.file.read())
            
            self._send_json({"status": "success", "url": f"/uploads/{filename}"})
        except Exception as e:
            self.send_error(500, str(e))

if __name__ == "__main__":
    # Allow address reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
        print(f"Serving {args.dir} at http://{args.host}:{args.port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
