import os
import re
import yaml
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

REPORT_DIR = "reports"
INDEX_FILE = "index.html"
TEMPLATE_DIR = "templates"

def get_report_metadata(filepath):
    filename = os.path.basename(filepath)
    date_str = filename.split('.')[0]
    
    # Try to extract date from filename (YYYY-MM-DD)
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        date_str = match.group(1)

    with open(filepath, 'r') as f:
        content = f.read()

    # Parse YAML frontmatter if it exists
    # Format: 
    # ---
    # title: My Title
    # author: Morty
    # ---
    metadata = {
        "title": filename,
        "author": "System",
        "date": date_str,
        "tags": ["report"],
        "summary": "",
        "file": filepath
    }

    frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if frontmatter_match:
        try:
            yaml_data = yaml.safe_load(frontmatter_match.group(1))
            if yaml_data:
                metadata.update(yaml_data)
            # Remove frontmatter for summary extraction
            body = content[frontmatter_match.end():]
        except Exception as e:
            print(f"Error parsing YAML in {filename}: {e}")
            body = content
    else:
        body = content

    # Fallback title if not in YAML
    if metadata["title"] == filename:
        title_match = re.search(r'^#\s+(.*)', body, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1)

    # Simple summary: first 200 chars of body
    clean_body = re.sub(r'#+\s+', '', body) # Remove headers
    metadata["summary"] = clean_body.strip()[:300] + "..."
        
    return metadata

def generate():
    reports = []
    if os.path.exists(REPORT_DIR):
        files = sorted(os.listdir(REPORT_DIR), reverse=True)
        for f in files:
            if f.endswith(".md"):
                reports.append(get_report_metadata(os.path.join(REPORT_DIR, f)))
    
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("index.jinja2")
    
    output = template.render(
        reports=reports,
        now=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    
    with open(INDEX_FILE, "w") as f:
        f.write(output)
    
    print(f"Generated {INDEX_FILE} with {len(reports)} reports using Jinja2.")

if __name__ == "__main__":
    generate()
