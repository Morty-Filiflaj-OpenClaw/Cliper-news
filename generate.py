import os
import re
import yaml
from markdown_it import MarkdownIt
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

REPORT_DIR = "reports"
OUTPUT_DIR = "articles"
INDEX_FILE = "index.html"
TEMPLATE_DIR = "templates"

def get_report_metadata(filepath):
    filename = os.path.basename(filepath)
    date_str = filename.split('.')[0]
    
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        date_str = match.group(1)

    with open(filepath, 'r') as f:
        content = f.read()

    metadata = {
        "title": filename.replace('.md', '').replace('-', ' ').title(),
        "author": "System",
        "date": date_str,
        "tags": ["report"],
        "summary": "",
        "file": filepath
    }

    body = content
    frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if frontmatter_match:
        try:
            yaml_data = yaml.safe_load(frontmatter_match.group(1))
            if yaml_data:
                metadata.update(yaml_data)
            body = content[frontmatter_match.end():]
        except Exception as e:
            print(f"Error parsing YAML in {filename}: {e}")

    if metadata["title"] == filename.replace('.md', '').replace('-', ' ').title():
        title_match = re.search(r'^#\s+(.*)', body, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1)

    clean_body = re.sub(r'#+\s+', '', body)
    metadata["summary"] = clean_body.strip()[:300] + "..."
    metadata["body"] = body

    return metadata

def generate():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    index_template = env.get_template("index.jinja2")
    article_template = env.get_template("article.jinja2")
    
    md = MarkdownIt().enable('table')
    
    reports = []
    if os.path.exists(REPORT_DIR):
        files = sorted(os.listdir(REPORT_DIR), reverse=True)
        for f in files:
            if f.endswith(".md"):
                meta = get_report_metadata(os.path.join(REPORT_DIR, f))
                
                # Pre-render markdown to HTML
                html_body = md.render(meta["body"])
                
                # Generate static article HTML
                article_filename = f.replace('.md', '.html')
                article_path = os.path.join(OUTPUT_DIR, article_filename)
                
                article_html = article_template.render(
                    title=meta["title"],
                    date=meta["date"],
                    author=meta.get("author", "System"),
                    tags=meta.get("tags", []),
                    body=html_body
                )
                
                with open(article_path, "w") as af:
                    af.write(article_html)
                
                # Update link to point to static HTML
                meta["link"] = f"{OUTPUT_DIR}/{article_filename}"
                reports.append(meta)
    
    # Generate index
    output = index_template.render(
        reports=reports,
        now=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    
    with open(INDEX_FILE, "w") as f:
        f.write(output)
    
    print(f"Generated {INDEX_FILE} + {len(reports)} static articles in {OUTPUT_DIR}/")

if __name__ == "__main__":
    generate()
