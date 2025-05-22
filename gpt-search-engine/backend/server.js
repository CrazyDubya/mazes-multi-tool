// backend/server.js

const express = require('express');
const axios = require('axios');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const cors = require('cors');
const dotenv = require('dotenv');
const fs = require('fs');
const path = require('path');
const xss = require('xss');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(express.json());
app.use(cors({
    origin: 'https://yourdomain.com' // Replace with your actual domain
}));

// Rate Limiting
const limiter = rateLimit({
    windowMs: 1 * 60 * 1000, // 1 minute
    max: 60 // limit each IP to 60 requests per windowMs
});
app.use(limiter);

// Log file setup
const logFilePath = path.join(__dirname, 'search_logs.json');

// Initialize log file if it doesn't exist
if (!fs.existsSync(logFilePath)) {
    fs.writeFileSync(logFilePath, JSON.stringify({}));
}

// Helper function to log searches
const logSearch = (query) => {
    const data = JSON.parse(fs.readFileSync(logFilePath, 'utf-8'));
    const sanitizedQuery = xss(query.trim().toLowerCase());

    if (data[sanitizedQuery]) {
        data[sanitizedQuery] += 1;
    } else {
        data[sanitizedQuery] = 1;
    }

    fs.writeFileSync(logFilePath, JSON.stringify(data, null, 2));
};

// API Endpoint
app.post('/api/search', async (req, res) => {
    try {
        let { query, start } = req.body;

        // Input Validation and Sanitization
        if (typeof query !== 'string' || query.trim() === '') {
            return res.status(400).json({ error: 'Invalid query parameter.' });
        }

        query = xss(query.trim());

        // Optional: Pagination
        start = parseInt(start) || 1;
        if (start < 1) start = 1;

        // Log the search
        logSearch(query);

        // Construct the search query
        const searchQuery = `site:chatgpt.com ${query}`;

        // Google Custom Search API Request
        const response = await axios.get('https://www.googleapis.com/customsearch/v1', {
            params: {
                key: process.env.GOOGLE_API_KEY,
                cx: process.env.GOOGLE_CSE_ID,
                q: searchQuery,
                start: start
            }
        });

        res.json(response.data);
    } catch (error) {
        console.error('Error in /api/search:', error.message);
        res.status(500).json({ error: 'An error occurred while processing your request.' });
    }
});

// Serve frontend static files
app.use(express.static(path.join(__dirname, '../frontend')));

// Start Server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});