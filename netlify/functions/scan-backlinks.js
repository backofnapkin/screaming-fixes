const https = require('https');
const http = require('http');

exports.handler = async (event, context) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    const { domain } = JSON.parse(event.body || '{}');

    if (!domain) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'Domain is required' })
      };
    }

    const normalizedDomain = domain
      .toLowerCase()
      .replace(/^https?:\/\//, '')
      .replace(/^www\./, '')
      .replace(/\/$/, '')
      .split('/')[0];

    const login = process.env.DATAFORSEO_LOGIN;
    const password = process.env.DATAFORSEO_PASSWORD;

    if (!login || !password) {
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ error: 'API not configured' })
      };
    }

    console.log('Starting scan for domain:', normalizedDomain);

    const apiResult = await callDataForSEO(normalizedDomain, login, password);

    if (apiResult.error) {
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ error: apiResult.error })
      };
    }

    console.log('DataForSEO returned', apiResult.results.length, 'grouped URLs');

    // Check which URLs are actually 404/410 (dead pages)
    const deadPages = await filterDeadPages(apiResult.results, normalizedDomain);

    console.log('Found', deadPages.length, 'dead pages with backlinks');

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        domain: normalizedDomain,
        scanned_at: new Date().toISOString(),
        results: deadPages,
        debug: {
          total_urls_from_api: apiResult.results.length,
          urls_checked: Math.min(apiResult.results.length, 100),
          dead_pages_found: deadPages.length
        }
      })
    };

  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: 'Internal server error: ' + error.message })
    };
  }
};

/**
 * Check URL status and filter to only 404/410 pages
 * Checks up to 100 URLs to avoid timeout
 */
async function filterDeadPages(results, domain) {
  const deadPages = [];
  const maxChecks = 100; // Limit to avoid Netlify timeout
  const urlsToCheck = results.slice(0, maxChecks);

  // Check URLs in parallel batches of 10 for speed
  const batchSize = 10;

  for (let i = 0; i < urlsToCheck.length; i += batchSize) {
    const batch = urlsToCheck.slice(i, i + batchSize);

    const statusChecks = batch.map(async (item) => {
      // Build full URL from the target_url or dead_page path
      let urlToCheck = item.target_url || item.dead_page;

      // If it's just a path, prepend the domain
      if (urlToCheck && !urlToCheck.startsWith('http')) {
        urlToCheck = 'https://' + domain + (urlToCheck.startsWith('/') ? '' : '/') + urlToCheck;
      }

      if (!urlToCheck) {
        return null;
      }

      try {
        const status = await checkUrlStatus(urlToCheck);

        if (status === 404 || status === 410) {
          return {
            dead_page: urlToCheck,
            dead_page_path: item.dead_page || new URL(urlToCheck).pathname,
            status_code: status,
            backlink_count: item.backlink_count || 0,
            referring_domains: item.referring_domains_count || 0,
            top_referrers: item.top_referrers || []
          };
        }
      } catch (e) {
        console.log('Error checking URL:', urlToCheck, e.message);
      }

      return null;
    });

    const batchResults = await Promise.all(statusChecks);

    for (const result of batchResults) {
      if (result) {
        deadPages.push(result);
      }
    }
  }

  // Sort by backlink count descending
  deadPages.sort((a, b) => b.backlink_count - a.backlink_count);

  return deadPages;
}

/**
 * Check HTTP status of a URL
 * Returns status code or 0 on error
 */
function checkUrlStatus(url) {
  return new Promise((resolve) => {
    const timeout = 8000; // 8 second timeout per URL

    let parsedUrl;
    try {
      parsedUrl = new URL(url);
    } catch (e) {
      resolve(0);
      return;
    }

    const protocol = parsedUrl.protocol === 'https:' ? https : http;

    const options = {
      hostname: parsedUrl.hostname,
      path: parsedUrl.pathname + parsedUrl.search,
      method: 'HEAD',
      timeout: timeout,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; ScreamingFixes/1.0; +https://screamingfixes.com)'
      }
    };

    const req = protocol.request(options, (res) => {
      resolve(res.statusCode);
    });

    req.on('error', () => {
      // Try GET if HEAD fails (some servers don't support HEAD)
      const getReq = protocol.request({ ...options, method: 'GET' }, (res) => {
        res.destroy(); // Don't download body
        resolve(res.statusCode);
      });

      getReq.on('error', () => resolve(0));
      getReq.on('timeout', () => {
        getReq.destroy();
        resolve(0);
      });

      getReq.end();
    });

    req.on('timeout', () => {
      req.destroy();
      resolve(0);
    });

    req.end();
  });
}

/**
 * Call DataForSEO API to get backlinks
 */
function callDataForSEO(domain, login, password) {
  return new Promise((resolve) => {
    const auth = Buffer.from(login + ':' + password).toString('base64');

    const postData = JSON.stringify([{
      target: domain,
      limit: 1000,
      mode: 'as_is'
    }]);

    const options = {
      hostname: 'api.dataforseo.com',
      path: '/v3/backlinks/backlinks/live',
      method: 'POST',
      headers: {
        'Authorization': 'Basic ' + auth,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          const response = JSON.parse(data);

          if (response.status_code !== 20000) {
            resolve({ error: response.status_message || 'API error' });
            return;
          }

          // Get items from the nested result structure
          const items = response.tasks &&
                       response.tasks[0] &&
                       response.tasks[0].result &&
                       response.tasks[0].result[0] &&
                       response.tasks[0].result[0].items
                       ? response.tasks[0].result[0].items
                       : [];

          console.log('DataForSEO returned', items.length, 'backlink items');

          // Group backlinks by target URL
          const groupedByTarget = {};

          for (const link of items) {
            const targetUrl = link.url_to;
            if (!targetUrl) continue;

            let targetPath;
            try {
              targetPath = new URL(targetUrl).pathname;
            } catch (e) {
              targetPath = targetUrl;
            }

            if (!groupedByTarget[targetPath]) {
              groupedByTarget[targetPath] = {
                dead_page: targetPath,
                target_url: targetUrl,
                backlink_count: 0,
                referring_domains: [],
                top_referrers: [],
                status_code: null
              };
            }

            groupedByTarget[targetPath].backlink_count++;

            const domainFrom = link.domain_from;
            if (domainFrom && !groupedByTarget[targetPath].referring_domains.includes(domainFrom)) {
              groupedByTarget[targetPath].referring_domains.push(domainFrom);

              // Add to top referrers (limit to 10)
              if (groupedByTarget[targetPath].top_referrers.length < 10) {
                groupedByTarget[targetPath].top_referrers.push({
                  domain: domainFrom,
                  url: link.url_from || '',
                  domain_rank: link.domain_from_rank || 0,
                  backlinks: 1
                });
              }
            }
          }

          // Convert to array and add referring_domains_count
          const results = Object.values(groupedByTarget).map(item => ({
            ...item,
            referring_domains_count: item.referring_domains.length,
            referring_domains: undefined // Remove the array, keep just the count
          }));

          // Sort by backlink count descending
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
