const https = require('https');

// Rate limit storage (in production, use a database like Netlify Blobs or Redis)
// For now, this resets on each deploy - we'll improve later
const rateLimitCache = new Map();

exports.handler = async (event, context) => {
  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json'
  };

  // Handle preflight
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  // Only allow POST
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    const { domain, site_url } = JSON.parse(event.body || '{}');

    if (!domain) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'Domain is required' })
      };
    }

    // Normalize domain
    const normalizedDomain = domain
      .toLowerCase()
      .replace(/^https?:\/\//, '')
      .replace(/^www\./, '')
      .replace(/\/$/, '')
      .split('/')[0];

    // Check rate limit (1 per day per domain)
    const today = new Date().toISOString().split('T')[0];
    const rateLimitKey = `${normalizedDomain}-${today}`;
    
    if (rateLimitCache.has(rateLimitKey)) {
      return {
        statusCode: 429,
        headers,
        body: JSON.stringify({ 
          error: 'Rate limit exceeded',
          message: 'Free scan limit reached for this domain. Try again tomorrow or add your own DataForSEO API key.',
          next_scan_available: 'tomorrow'
        })
      };
    }

    // Get credentials from environment variables
    const login = process.env.DATAFORSEO_LOGIN;
    const password = process.env.DATAFORSEO_PASSWORD;

    if (!login || !password) {
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ error: 'API not configured' })
      };
    }

    // Call DataForSEO API
    const apiResult = await callDataForSEO(normalizedDomain, login, password);

    if (apiResult.error) {
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ error: apiResult.error })
      };
    }

    // Mark rate limit
    rateLimitCache.set(rateLimitKey, true);

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        domain: normalizedDomain,
        scanned_at: new Date().toISOString(),
        results: apiResult.results
      })
    };

  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: 'Internal server error' })
    };
  }
};

async function callDataForSEO(domain, login, password) {
  return new Promise((resolve) => {
    const auth = Buffer.from(`${login}:${password}`).toString('base64');
    
    // Step 1: Get backlinks for the domain
    const postData = JSON.stringify([{
      target: domain,
      limit: 1000,
      mode: "as_is",
      filters: ["is_lost", "=", false]
    }]);

    const options = {
      hostname: 'api.dataforseo.com',
      path: '/v3/backlinks/backlinks/live',
      method: 'POST',
      headers: {
        'Authorization': `Basic ${auth}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', async () => {
        try {
          const response = JSON.parse(data);
          
          if (response.status_code !== 20000) {
            resolve({ error: response.status_message || 'API error' });
            return;
          }

          const backlinks = response.tasks?.[0]?.result || [];
          
          // Group backlinks by target URL and check for 404s
          const groupedByTarget = {};
          
          for (const link of backlinks) {
            const targetUrl = link.url_to;
            const targetPath = new URL(targetUrl).pathname;
            
            if (!groupedByTarget[targetPath]) {
              groupedByTarget[targetPath] = {
                dead_page: targetPath,
                target_url: targetUrl,
                backlink_count: 0,
                referring_domains: new Set(),
                top_referrers: [],
                status_code: null
              };
            }
            
            groupedByTarget[targetPath].backlink_count++;
            groupedByTarget[targetPath].referring_domains.add(link.domain_from);
            
            // Add to top referrers (limit to 10)
            if (groupedByTarget[targetPath].top_referrers.length < 10) {
              groupedByTarget[targetPath].top_referrers.push({
                domain: link.domain_from,
                url: link.url_from,
                domain_rank: link.domain_from_rank || 0,
                backlinks: 1
              });
            }
          }

          // Check which pages are 404
          const results = [];
          const targetUrls = Object.values(groupedByTarget);
          
          // Check status codes (limit concurrent checks)
          for (const item of targetUrls.slice(0, 100)) {
            const status = await checkUrlStatus(item.target_url);
            if (status === 404 || status === 410 || status === 0) {
              item.status_code = status || 404;
              item.referring_domains = item.referring_domains.size;
              results.push(item);
            }
          }

          // Sort by backlink count
          results.sort((a, b) => b.backlink_count - a.backlink_count);

          resolve({ results: results.slice(0, 1000) });
          
        } catch (e) {
          console.error('Parse error:', e);
          resolve({ error: 'Failed to parse API response' });
        }
      });
    });

    req.on('error', (e) => {
      console.error('Request error:', e);
      resolve({ error: 'Failed to connect to API' });
    });

    req.write(postData);
    req.end();
  });
}

async function checkUrlStatus(url) {
  return new Promise((resolve) => {
    try {
      const urlObj = new URL(url);
      const options = {
        hostname: urlObj.hostname,
        path: urlObj.pathname + urlObj.search,
        method: 'HEAD',
        timeout: 5000
      };

      const req = https.request(options, (res) => {
        resolve(res.statusCode);
      });

      req.on('error', () => resolve(0));
      req.on('timeout', () => {
        req.destroy();
        resolve(0);
      });

      req.end();
    } catch {
      resolve(0);
    }
  });
}
```

4. Click **"Commit changes"**

---

## Step 5: Wait for Netlify to redeploy

Go back to your Netlify dashboard - it should automatically rebuild. Should take ~30 seconds.

---

## Step 6: Test the function

Once deployed, test by visiting:
```
https://screamingfixes.netlify.app/.netlify/functions/scan-backlinks
