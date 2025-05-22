Sure! Below is a complete guide to building your GPT Search Engine website, including all necessary code and instructions for setting up third-party services. This guide assumes you have a VPS and a domain already set up.

## Overview

The website will consist of:

1. **Frontend**: An HTML/CSS/JavaScript page that includes a search bar, displays search results, and includes tracking and branding elements.
2. **Backend**: A Node.js server using Express to handle API requests, interact with the Google Custom Search API, sanitize inputs, and log search queries.
3. **Third-Party Services**: Google Custom Search API for search functionality and Google Analytics for visitor tracking.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Third-Party Setup](#third-party-setup)
   - [1. Google Custom Search API](#1-google-custom-search-api)
   - [2. Google Analytics](#2-google-analytics)
3. [Backend Setup](#backend-setup)
   - [1. Directory Structure](#1-directory-structure)
   - [2. server.js](#2-serverjs)
   - [3. package.json](#3-packagejson)
   - [4. Environment Variables](#4-environment-variables)
4. [Frontend Setup](#frontend-setup)
   - [1. index.html](#1-indexhtml)
   - [2. styles.css](#2-stylescss)
   - [3. script.js](#3-scriptjs)
5. [Deployment Instructions](#deployment-instructions)
6. [Security Considerations](#security-considerations)

---

## Prerequisites

- **VPS**: Ensure your VPS is set up with Node.js installed.
- **Domain**: Your domain should point to your VPS.
- **Basic Knowledge**: Familiarity with SSH, terminal commands, and basic web development.

---

## Third-Party Setup

### 1. Google Custom Search API

To perform Google searches programmatically, you'll need to set up the Google Custom Search API.

**Steps:**

1. **Create a Google Cloud Project:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Click on **Select a project** > **New Project**.
   - Enter a project name and click **Create**.

2. **Enable Custom Search API:**
   - In the [APIs & Services Dashboard](https://console.cloud.google.com/apis/dashboard), click **Enable APIs and Services**.
   - Search for **Custom Search API** and enable it.

3. **Obtain API Key:**
   - Go to **APIs & Services** > **Credentials**.
   - Click **Create Credentials** > **API Key**.
   - Copy the generated API key; you'll need it later.

4. **Set Up Custom Search Engine:**
   - Visit the [Custom Search Engine](https://cse.google.com/cse/all) page.
   - Click **Add**.
   - In the **Sites to search** field, enter `chatgpt.com`.
   - Configure other settings as desired and create the search engine.
   - After creation, go to the **Control Panel** of your CSE.
   - Note down the **Search Engine ID**; you'll need it later.

**Resources:**

- [Google Custom Search API Documentation](https://developers.google.com/custom-search/v1/overview)

### 2. Google Analytics

For visitor tracking, Google Analytics is recommended.

**Steps:**

1. **Create a Google Analytics Account:**
   - Go to [Google Analytics](https://analytics.google.com/).
   - Sign in with your Google account and set up a new property for your website.

2. **Obtain Tracking ID:**
   - After setting up, you'll receive a Tracking ID (e.g., `UA-XXXXXXXXX-X`).

3. **Integrate Tracking Code:**
   - You'll add the provided tracking script to your `index.html` file (instructions below).

**Resources:**

- [Google Analytics Setup Guide](https://support.google.com/analytics/answer/1008015?hl=en)

---

## Backend Setup

We'll use Node.js with Express to handle API requests securely.

### 1. Directory Structure

```
gpt-search-engine/
├── backend/
│   ├── server.js
│   ├── package.json
│   └── .env
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
```

### 2. `server.js`

Create a file named `server.js` inside the `backend` directory with the following content:

```javascript
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
```

**Explanation:**

- **Security Middlewares**:
  - `helmet`: Sets various HTTP headers for security.
  - `express-rate-limit`: Limits repeated requests to public APIs.
  - `cors`: Enables Cross-Origin Resource Sharing.
  - `xss`: Sanitizes user input to prevent XSS attacks.

- **Logging**:
  - Logs search queries in `search_logs.json` without identifying information.

- **API Endpoint**:
  - `/api/search`: Accepts POST requests with `query` and optional `start` parameters.
  - Sanitizes inputs and interacts with the Google Custom Search API.
  - Returns search results to the frontend.

### 3. `package.json`

Create a `package.json` file inside the `backend` directory:

```json
// backend/package.json

{
  "name": "gpt-search-engine-backend",
  "version": "1.0.0",
  "description": "Backend for GPT Search Engine",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "axios": "^1.4.0",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "express": "^4.18.2",
    "express-rate-limit": "^6.7.0",
    "helmet": "^7.0.0",
    "xss": "^1.0.14"
  }
}
```

**Installation:**

Navigate to the `backend` directory and install dependencies:

```bash
cd backend
npm install
```

### 4. Environment Variables

Create a `.env` file inside the `backend` directory to store sensitive information:

```env
// backend/.env

PORT=3000
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
GOOGLE_CSE_ID=YOUR_GOOGLE_CSE_ID
```

**Replace:**

- `YOUR_GOOGLE_API_KEY` with the API key obtained from Google Custom Search API.
- `YOUR_GOOGLE_CSE_ID` with the Custom Search Engine ID.

**Note:** Ensure that `.env` is added to `.gitignore` if you use version control to prevent exposing sensitive data.

---

## Frontend Setup

Create the frontend files inside the `frontend` directory.

### 1. `index.html`

Create an `index.html` file with the following content:

```html
<!-- frontend/index.html -->

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPT Search Engine</title>
    <meta name="description" content="Search within ChatGPT.com using GPT Search Engine.">
    <meta name="keywords" content="GPT, Search, ChatGPT, AI Search Engine">
    <meta name="author" content="Your Name">

    <!-- Bootstrap CSS via CDN -->
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
      rel="stylesheet"
      integrity="sha384-GtvMKA+P1PfYJp2iECs1CA+R3oKqx7p+g9+LZLaM6IYhUz1x3zwPPCeSPkh+XVFU"
      crossorigin="anonymous"
    >

    <!-- Custom CSS -->
    <link rel="stylesheet" href="styles.css">

    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=YOUR_GA_TRACKING_ID"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());

      gtag('config', 'YOUR_GA_TRACKING_ID');
    </script>
</head>
<body>
    <header class="bg-primary text-white text-center py-3">
        <h1>GPT Search Engine</h1>
    </header>

    <main class="container my-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <form id="search-form">
                    <div class="input-group">
                        <input type="text" id="search-input" class="form-control" placeholder="Search ChatGPT.com..." required>
                        <button class="btn btn-primary" type="submit">Search</button>
                    </div>
                </form>
            </div>
        </div>

        <div id="results" class="mt-5"></div>

        <nav id="pagination" aria-label="Search results pages" class="mt-4">
            <ul class="pagination justify-content-center">
                <!-- Pagination buttons will be injected here -->
            </ul>
        </nav>
    </main>

    <footer class="bg-light text-center py-3">
        <span>Your ad here</span>
    </footer>

    <!-- Bootstrap JS via CDN -->
    <script
      src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"
      integrity="sha384-qjD9K3nOZxA5+QlQfXriHgWrJ9OP3Sl+xqjDtaAe5xPB+tE5NgP7/Weha4Q6Eh/3"
      crossorigin="anonymous"
    ></script>

    <!-- jQuery via CDN -->
    <script
      src="https://code.jquery.com/jquery-3.7.0.min.js"
      integrity="sha256-3fhjoIRzz9A6+K/Z3UqXc+RjA3CpK+U9q+Pvz5x1S+k="
      crossorigin="anonymous"
    ></script>

    <!-- Custom JS -->
    <script src="script.js"></script>
</body>
</html>
```

**Replace:**

- `YOUR_GA_TRACKING_ID` with your actual Google Analytics Tracking ID.

**Explanation:**

- **Meta Tags**: Improve SEO and provide metadata.
- **Bootstrap**: For responsive design and styling.
- **Google Analytics**: Tracks visitor data.
- **Header & Footer**: Branding and ad placeholder.
- **Search Form**: Allows users to input search queries.
- **Results & Pagination**: Display search results and navigate through pages.

### 2. `styles.css`

Create a `styles.css` file with the following content:

```css
/* frontend/styles.css */

body {
    background-color: #f8f9fa;
}

header h1 {
    font-size: 2.5rem;
}

footer {
    position: fixed;
    width: 100%;
    bottom: 0;
}

#results .result-item {
    padding: 15px;
    border-bottom: 1px solid #dee2e6;
}

#results .result-item:last-child {
    border-bottom: none;
}

#results .result-item a {
    text-decoration: none;
    color: #0d6efd;
}

#results .result-item a:hover {
    text-decoration: underline;
}
```

**Explanation:**

- **Styling**: Enhances the appearance of the website, including the header, footer, and search results.

### 3. `script.js`

Create a `script.js` file with the following content:

```javascript
// frontend/script.js

$(document).ready(function() {
    const $searchForm = $('#search-form');
    const $searchInput = $('#search-input');
    const $results = $('#results');
    const $pagination = $('#pagination .pagination');

    let currentPage = 1;
    const resultsPerPage = 10;

    $searchForm.on('submit', function(e) {
        e.preventDefault();
        const query = $searchInput.val().trim();
        if (query === '') return;

        currentPage = 1;
        performSearch(query, currentPage);
    });

    function performSearch(query, page) {
        $results.html('<p>Loading...</p>');
        $pagination.empty();

        $.ajax({
            url: '/api/search',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                query: query,
                start: (page - 1) * resultsPerPage + 1
            }),
            success: function(data) {
                displayResults(data, query);
                setupPagination(data, query);
            },
            error: function(err) {
                console.error(err);
                $results.html('<p>An error occurred while fetching results.</p>');
            }
        });
    }

    function displayResults(data, query) {
        if (!data.items || data.items.length === 0) {
            $results.html('<p>No results found.</p>');
            return;
        }

        let html = '';
        data.items.forEach(item => {
            html += `
                <div class="result-item">
                    <h5><a href="${item.link}" target="_blank">${item.title}</a></h5>
                    <p>${item.snippet}</p>
                    <a href="${item.link}" target="_blank">${item.link}</a>
                </div>
            `;
        });

        $results.html(html);
    }

    function setupPagination(data, query) {
        const totalResults = parseInt(data.searchInformation.totalResults);
        const totalPages = Math.ceil(totalResults / resultsPerPage);
        const visiblePages = 5;
        let startPage = Math.max(currentPage - Math.floor(visiblePages / 2), 1);
        let endPage = startPage + visiblePages - 1;

        if (endPage > totalPages) {
            endPage = totalPages;
            startPage = Math.max(endPage - visiblePages + 1, 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const activeClass = i === currentPage ? 'active' : '';
            $pagination.append(`
                <li class="page-item ${activeClass}">
                    <a class="page-link" href="#">${i}</a>
                </li>
            `);
        }

        // Handle page click
        $('.page-link').on('click', function(e) {
            e.preventDefault();
            const selectedPage = parseInt($(this).text());
            if (selectedPage !== currentPage) {
                currentPage = selectedPage;
                performSearch(query, currentPage);
                $('html, body').animate({ scrollTop: 0 }, 'fast');
            }
        });
    }
});
```

**Explanation:**

- **Search Functionality**: Handles form submission, sends AJAX requests to the backend, and displays results.
- **Pagination**: Dynamically creates pagination controls based on the number of results.
- **Error Handling**: Displays messages if no results are found or if an error occurs.

---

## Deployment Instructions

### 1. Upload Files to VPS

Assuming you have SSH access to your VPS, follow these steps:

1. **Connect to VPS via SSH:**

   ```bash
   ssh username@your_vps_ip
   ```

2. **Install Node.js and npm** (if not already installed):

   ```bash
   # Update package list
   sudo apt update

   # Install Node.js (latest LTS)
   curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
   sudo apt install -y nodejs

   # Verify installation
   node -v
   npm -v
   ```

3. **Transfer Project Files:**

   You can use `scp`, `git`, or any other method to transfer your project files to the VPS. Here's an example using `scp`:

   ```bash
   # From your local machine
   scp -r gpt-search-engine/ username@your_vps_ip:/home/username/
   ```

4. **Navigate to Backend Directory and Install Dependencies:**

   ```bash
   cd /home/username/gpt-search-engine/backend
   npm install
   ```

5. **Configure Environment Variables:**

   Edit the `.env` file with your actual API keys:

   ```bash
   nano .env
   ```

   Replace `YOUR_GOOGLE_API_KEY` and `YOUR_GOOGLE_CSE_ID` with your actual credentials. Save and exit (`Ctrl + X`, then `Y`, then `Enter`).

6. **Start the Server:**

   For production, it's recommended to use a process manager like `pm2`:

   ```bash
   sudo npm install -g pm2
   pm2 start server.js --name gpt-search-engine
   pm2 save
   pm2 startup
   ```

   This ensures your server runs continuously and restarts on system reboots.

7. **Configure Nginx as a Reverse Proxy** (optional but recommended):

   If you want to serve your application on port 80 (HTTP) or 443 (HTTPS), setting up Nginx as a reverse proxy is advisable.

   **Install Nginx:**

   ```bash
   sudo apt install nginx
   ```

   **Configure Nginx:**

   Create a new server block:

   ```bash
   sudo nano /etc/nginx/sites-available/gpt-search-engine
   ```

   Add the following configuration (replace `yourdomain.com` with your actual domain):

   ```nginx
   server {
       listen 80;
       server_name yourdomain.com www.yourdomain.com;

       location / {
           proxy_pass http://localhost:3000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

   **Enable the Configuration:**

   ```bash
   sudo ln -s /etc/nginx/sites-available/gpt-search-engine /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

   **Enable HTTPS with Let's Encrypt** (optional but recommended):

   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

   Follow the prompts to obtain and install SSL certificates.

---

## Security Considerations

1. **Sanitize User Inputs:**
   - Already implemented using the `xss` library to prevent Cross-Site Scripting (XSS) attacks.

2. **Rate Limiting:**
   - Prevents abuse by limiting the number of requests per IP address.

3. **HTTP Headers:**
   - `helmet` sets secure HTTP headers to protect against common vulnerabilities.

4. **Environment Variables:**
   - Store sensitive data like API keys in `.env` files, which should not be committed to version control.

5. **HTTPS:**
   - Ensure your website is served over HTTPS to encrypt data in transit.

6. **Logging:**
   - Search logs are stored without identifying information. Ensure log files are secured and not publicly accessible.

7. **CORS Configuration:**
   - Restrict API access to your domain to prevent unauthorized usage.

---

## Complete Final Workable Code

### 1. Backend

#### `server.js`

```javascript
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
```

#### `package.json`

```json
// backend/package.json

{
  "name": "gpt-search-engine-backend",
  "version": "1.0.0",
  "description": "Backend for GPT Search Engine",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "axios": "^1.4.0",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "express": "^4.18.2",
    "express-rate-limit": "^6.7.0",
    "helmet": "^7.0.0",
    "xss": "^1.0.14"
  }
}
```

#### `.env`

```env
// backend/.env

PORT=3000
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
GOOGLE_CSE_ID=YOUR_GOOGLE_CSE_ID
```

**Replace** `YOUR_GOOGLE_API_KEY` and `YOUR_GOOGLE_CSE_ID` with your actual credentials.

### 2. Frontend

#### `index.html`

```html
<!-- frontend/index.html -->

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPT Search Engine</title>
    <meta name="description" content="Search within ChatGPT.com using GPT Search Engine.">
    <meta name="keywords" content="GPT, Search, ChatGPT, AI Search Engine">
    <meta name="author" content="Your Name">

    <!-- Bootstrap CSS via CDN -->
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
      rel="stylesheet"
      integrity="sha384-GtvMKA+P1PfYJp2iECs1CA+R3oKqx7p+g9+LZLaM6IYhUz1x3zwPPCeSPkh+XVFU"
      crossorigin="anonymous"
    >

    <!-- Custom CSS -->
    <link rel="stylesheet" href="styles.css">

    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=YOUR_GA_TRACKING_ID"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());

      gtag('config', 'YOUR_GA_TRACKING_ID');
    </script>
</head>
<body>
    <header class="bg-primary text-white text-center py-3">
        <h1>GPT Search Engine</h1>
    </header>

    <main class="container my-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <form id="search-form">
                    <div class="input-group">
                        <input type="text" id="search-input" class="form-control" placeholder="Search ChatGPT.com..." required>
                        <button class="btn btn-primary" type="submit">Search</button>
                    </div>
                </form>
            </div>
        </div>

        <div id="results" class="mt-5"></div>

        <nav id="pagination" aria-label="Search results pages" class="mt-4">
            <ul class="pagination justify-content-center">
                <!-- Pagination buttons will be injected here -->
            </ul>
        </nav>
    </main>

    <footer class="bg-light text-center py-3">
        <span>Your ad here</span>
    </footer>

    <!-- Bootstrap JS via CDN -->
    <script
      src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"
      integrity="sha384-qjD9K3nOZxA5+QlQfXriHgWrJ9OP3Sl+xqjDtaAe5xPB+tE5NgP7/Weha4Q6Eh/3"
      crossorigin="anonymous"
    ></script>

    <!-- jQuery via CDN -->
    <script
      src="https://code.jquery.com/jquery-3.7.0.min.js"
      integrity="sha256-3fhjoIRzz9A6+K/Z3UqXc+RjA3CpK+U9q+Pvz5x1S+k="
      crossorigin="anonymous"
    ></script>

    <!-- Custom JS -->
    <script src="script.js"></script>
</body>
</html>
```

**Replace** `YOUR_GA_TRACKING_ID` with your actual Google Analytics Tracking ID.

#### `styles.css`

```css
/* frontend/styles.css */

body {
    background-color: #f8f9fa;
}

header h1 {
    font-size: 2.5rem;
}

footer {
    position: fixed;
    width: 100%;
    bottom: 0;
}

#results .result-item {
    padding: 15px;
    border-bottom: 1px solid #dee2e6;
}

#results .result-item:last-child {
    border-bottom: none;
}

#results .result-item a {
    text-decoration: none;
    color: #0d6efd;
}

#results .result-item a:hover {
    text-decoration: underline;
}
```

#### `script.js`

```javascript
// frontend/script.js

$(document).ready(function() {
    const $searchForm = $('#search-form');
    const $searchInput = $('#search-input');
    const $results = $('#results');
    const $pagination = $('#pagination .pagination');

    let currentPage = 1;
    const resultsPerPage = 10;

    $searchForm.on('submit', function(e) {
        e.preventDefault();
        const query = $searchInput.val().trim();
        if (query === '') return;

        currentPage = 1;
        performSearch(query, currentPage);
    });

    function performSearch(query, page) {
        $results.html('<p>Loading...</p>');
        $pagination.empty();

        $.ajax({
            url: '/api/search',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                query: query,
                start: (page - 1) * resultsPerPage + 1
            }),
            success: function(data) {
                displayResults(data, query);
                setupPagination(data, query);
            },
            error: function(err) {
                console.error(err);
                $results.html('<p>An error occurred while fetching results.</p>');
            }
        });
    }

    function displayResults(data, query) {
        if (!data.items || data.items.length === 0) {
            $results.html('<p>No results found.</p>');
            return;
        }

        let html = '';
        data.items.forEach(item => {
            html += `
                <div class="result-item">
                    <h5><a href="${item.link}" target="_blank">${item.title}</a></h5>
                    <p>${item.snippet}</p>
                    <a href="${item.link}" target="_blank">${item.link}</a>
                </div>
            `;
        });

        $results.html(html);
    }

    function setupPagination(data, query) {
        const totalResults = parseInt(data.searchInformation.totalResults);
        const totalPages = Math.ceil(totalResults / resultsPerPage);
        const visiblePages = 5;
        let startPage = Math.max(currentPage - Math.floor(visiblePages / 2), 1);
        let endPage = startPage + visiblePages - 1;

        if (endPage > totalPages) {
            endPage = totalPages;
            startPage = Math.max(endPage - visiblePages + 1, 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const activeClass = i === currentPage ? 'active' : '';
            $pagination.append(`
                <li class="page-item ${activeClass}">
                    <a class="page-link" href="#">${i}</a>
                </li>
            `);
        }

        // Handle page click
        $('.page-link').on('click', function(e) {
            e.preventDefault();
            const selectedPage = parseInt($(this).text());
            if (selectedPage !== currentPage) {
                currentPage = selectedPage;
                performSearch(query, currentPage);
                $('html, body').animate({ scrollTop: 0 }, 'fast');
            }
        });
    }
});
```

---

## Conclusion

You now have a complete GPT Search Engine website that allows users to search within `chatgpt.com`, view paginated results, and tracks visitor data. The backend securely interacts with the Google Custom Search API, logs search queries, and ensures that user inputs are sanitized. The frontend provides a user-friendly interface with responsive design elements.

**Remember to:**

- Replace placeholder values (`YOUR_GOOGLE_API_KEY`, `YOUR_GOOGLE_CSE_ID`, `YOUR_GA_TRACKING_ID`, `yourdomain.com`) with your actual credentials and domain.
- Secure your server and environment variables appropriately.
- Regularly monitor your logs and API usage to ensure everything operates smoothly.

Feel free to customize and expand upon this foundation to better suit your needs!