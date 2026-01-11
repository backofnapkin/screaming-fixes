const https = require('https');

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

    const apiResult = await callDataForSEO(normalizedDomain, login, password);

    if (apiResult.error) {
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ error: apiResult.error })
      };
    }

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
      body: JSON.stringify({ error: 'Internal server error: ' + error.message })
    };
  }
};

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

          const backlinks = response.tasks && response.tasks[0] && response.tasks[0].result ? response.tasks[0].result : [];
          
          const groupedByTarget = {};
          
          for (let i = 0; i < backlinks.length; i++) {
            const link = backlinks[i];
            const targetUrl = link.url_to;
            
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
            
            if (groupedByTarget[targetPath].referring_domains.indexOf(link.domain_from) === -1) {
              groupedByTarget[targetPath].referring_domains.push(link.domain_from);
            }
            
            if (groupedByTarget[targetPath].top_referrers.length < 10) {
              groupedByTarget[targetPath].top_referrers.push({
                domain: link.domain_from,
                url: link.url_from,
                domain_rank: link.domain_from_rank || 0,
                backlinks: 1
              });
            }
          }

          const results = [];
          const keys = Object.keys(groupedByTarget);
          
          for (let i = 0; i < keys.length; i++) {
            const item = groupedByTarget[keys[i]];
            item.referring_domains_count = item.referring_domains.length;
            delete item.referring_domains;
            results.push(item);
          }

          results.sort(function(a, b) {
            return b.backlink_count - a.backlink_count;
          });

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
