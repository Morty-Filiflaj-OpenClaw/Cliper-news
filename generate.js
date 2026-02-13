const fs = require('fs-extra');
const path = require('path');
const matter = require('gray-matter');
const marked = require('marked');
const ejs = require('ejs');

const REPORT_DIR = 'reports';
const PUBLIC_DIR = 'public';
const VIEWS_DIR = 'views';

async function generate() {
    console.log('Starting generation...');
    
    // Ensure public dir exists
    await fs.ensureDir(path.join(PUBLIC_DIR, 'reports'));

    // Get all md files
    if (!fs.existsSync(REPORT_DIR)) {
        console.log('No reports directory found.');
        return;
    }

    const files = await fs.readdir(REPORT_DIR);
    const reports = [];

    for (const file of files) {
        if (!file.endsWith('.md')) continue;

        const filePath = path.join(REPORT_DIR, file);
        const fileContent = await fs.readFile(filePath, 'utf-8');
        
        // Parse frontmatter
        const { data, content } = matter(fileContent);
        
        const filenameBase = path.basename(file, '.md');
        const htmlFilename = `${filenameBase}.html`;
        
        // Metadata
        const metadata = {
            title: data.title || filenameBase,
            author: data.author || 'System',
            date: data.date || extractDate(file) || new Date().toISOString().split('T')[0],
            tags: data.tags || ['report'],
            summary: data.summary || content.replace(/#+\s+/g, '').substring(0, 300) + '...',
            filenameBase: filenameBase, // for linking
            content: marked.parse(content) // Pre-render markdown
        };
        
        reports.push(metadata);

        // Render Article Page
        const articleHtml = await ejs.renderFile(path.join(VIEWS_DIR, 'article.ejs'), metadata);
        await fs.writeFile(path.join(PUBLIC_DIR, 'reports', htmlFilename), articleHtml);
        console.log(`Generated: reports/${htmlFilename}`);
    }

    // Sort reports by date/filename descending
    reports.sort((a, b) => (b.date + b.filenameBase).localeCompare(a.date + a.filenameBase));

    // Render Index Page
    const indexHtml = await ejs.renderFile(path.join(VIEWS_DIR, 'index.ejs'), {
        reports: reports,
        now: new Date().toISOString().replace('T', ' ').substring(0, 16)
    });
    await fs.writeFile(path.join(PUBLIC_DIR, 'index.html'), indexHtml);
    console.log('Generated: index.html');

    // Copy static files (new_article.html)
    // We can just copy it as is, but ensure it points to the right API endpoint (relative paths should work)
    if (await fs.pathExists('new_article.html')) {
        await fs.copy('new_article.html', path.join(PUBLIC_DIR, 'new_article.html'));
    }
}

function extractDate(filename) {
    const match = filename.match(/(\d{4}-\d{2}-\d{2})/);
    return match ? match[1] : null;
}

generate().catch(console.error);
