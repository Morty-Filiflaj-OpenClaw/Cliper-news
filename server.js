const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs-extra');
const path = require('path');
const { exec } = require('child_process');

const app = express();
const PORT = 8080;
const REPORT_DIR = 'reports';

app.use(bodyParser.json());

// Serve static files from 'public' directory
app.use(express.static('public'));

// API to save new articles
app.post('/api/save', async (req, res) => {
    try {
        const { filename, content } = req.body;
        
        if (!filename || !content) {
            return res.status(400).json({ error: 'Missing filename or content' });
        }

        // Security sanitization
        const safeFilename = path.basename(filename).replace(/[^a-zA-Z0-9-]/g, '') + '.md';
        const filePath = path.join(REPORT_DIR, safeFilename);

        await fs.ensureDir(REPORT_DIR);
        await fs.writeFile(filePath, content);

        console.log(`Saved article: ${safeFilename}`);

        // Trigger generation
        exec('node generate.js', (error, stdout, stderr) => {
            if (error) {
                console.error(`Generation error: ${error}`);
                return; // Don't fail the request, just log it
            }
            console.log(`Generation output: ${stdout}`);
        });

        res.json({ status: 'success', file: filePath });

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

// Fallback to index.html for 404s (optional, or just let express handle it)
// app.get('*', (req, res) => res.sendFile(path.resolve(__dirname, 'public', 'index.html')));

app.listen(PORT, () => {
    console.log(`Server running at http://0.0.0.0:${PORT}`);
    console.log(`Serving static content from ${path.join(__dirname, 'public')}`);
});
