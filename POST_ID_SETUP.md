# 🔧 Setting Up Post ID Extraction in Screaming Frog

**A one-time setup that unlocks bulk WordPress editing**

---

## Why You Need Post IDs

When you look at a URL like `https://example.com/how-to-start-a-food-truck/`, that's the human-friendly version. But WordPress doesn't use URLs internally — it uses **Post IDs**.

Every page and post in WordPress has a unique numeric ID like `6125`. When you want to edit content via the WordPress API, you need this number. Without it, WordPress doesn't know which content you're referring to.

**The good news:** Your WordPress site already contains Post IDs in the HTML. We just need to tell Screaming Frog to extract them during the crawl.

**Setup once, benefit forever.** After this 5-minute configuration, every future crawl will include Post IDs automatically.

---

## Requirements

- **Screaming Frog SEO Spider** (licensed version required for Custom Extraction)
- License cost: ~$259/year — incredible value for professional SEO tools
- Download: [screamingfrog.co.uk/seo-spider](https://www.screamingfrog.co.uk/seo-spider/)

---

## Step-by-Step Setup

### Step 1: Open Custom Extraction

1. Open Screaming Frog
2. Go to **Configuration → Custom → Extraction**
3. A dialog box will appear

### Step 2: Add New Extractor

1. Click **Add**
2. Set the following:

| Field | Value |
|-------|-------|
| **Name** | `post_id` |
| **Type** | Change dropdown from "XPath" to **Regex** |
| **Regex** | (see options below) |

### Step 3: Choose Your Regex Pattern

WordPress themes store Post IDs in different places. You'll need to check your site to see which one applies.

**How to check:** Visit any post on your site → Right-click → View Page Source → Search (Ctrl+F) for the patterns below.

---

#### Option A: Shortlink (Most Common)

**Look for this in your HTML:**
```html
<link rel="shortlink" href="https://yoursite.com/?p=6125">
```

**Regex to use:**
```
<link[^>]+rel=['"]shortlink['"][^>]+href=['"][^'"]*\?p=(\d+)
```

---

#### Option B: Body Class

**Look for this in your HTML:**
```html
<body class="post-template postid-6125 single">
```
or
```html
<body class="page-template page-id-6125">
```

**Regex to use:**
```
class=['"][^'"]*(?:postid|page-id)-(\d+)
```

---

#### Option C: Article ID

**Look for this in your HTML:**
```html
<article id="post-6125" class="post">
```

**Regex to use:**
```
<article[^>]+id=['"]post-(\d+)
```

---

#### Option D: REST API Link

**Look for this in your HTML:**
```html
<link rel="alternate" type="application/json" href="https://yoursite.com/wp-json/wp/v2/posts/6125">
```

**Regex to use:**
```
wp-json/wp/v2/posts/(\d+)
```

---

### Step 4: Save Your Configuration

1. Click **OK** to close the extraction dialog
2. Go to **Configuration → Profiles → Save Current Configuration as Default**
3. Now every future crawl includes Post ID extraction automatically

### Step 5: Run Your Crawl

1. Enter your website URL
2. Click **Start**
3. Wait for the crawl to complete

### Step 6: Verify It Worked

1. After the crawl completes, go to the **Internal** tab
2. Look for a column called **post_id** (or check Custom Extraction tab)
3. You should see numeric IDs like `6125`, `8472`, etc.

**If you see empty values:** Your theme may use a different method. Try another regex option above, or see the troubleshooting section below.

### Step 7: Export the Custom Extraction CSV

**Important:** The Post IDs are stored in a separate export from your reports.

1. After your crawl completes, go to **Bulk Export → Custom Extraction → post_id**
2. Save this CSV file — it contains your URLs mapped to Post IDs
3. Upload this file to Screaming Fixes to unlock **Full Mode**

### Step 8: Export Your Reports

Now export the report you want to fix:

- **Broken Links:** Bulk Export → Response Codes → Client Error (4xx) → Inlinks
- **Redirect Chains:** Reports → Redirects → All Redirects

**Note:** These report exports won't include the Post ID column. That's why you need to upload the Custom Extraction CSV separately in Step 7. Screaming Fixes will automatically match the two files together.

---

## Can't Find Your Post ID Pattern?

Every WordPress theme is different. If none of the options above work, here's a prompt you can use with any AI assistant (ChatGPT, Claude, etc.) to identify your site's pattern:

---

### AI Prompt for Finding Your Post ID Pattern

Copy and paste this prompt, replacing the HTML sample with your own:

```
I need to extract WordPress Post IDs from my website's HTML using Screaming Frog's Custom Extraction feature with Regex.

Here is a sample of my page's HTML source code:

[PASTE 50-100 LINES OF YOUR HTML HERE - from View Page Source]

Please analyze this HTML and:

1. Identify where the WordPress Post ID is stored (shortlink, body class, article tag, REST API link, or elsewhere)
2. Provide the exact Regex pattern I should use in Screaming Frog

The Post ID is a numeric value that WordPress uses internally to identify this specific page/post.
```

---

## Troubleshooting

### "I don't see any Post IDs after crawling"

1. **Check your Screaming Frog license** — Custom Extraction requires a paid license
2. **Try a different regex** — Your theme may store IDs differently than expected
3. **Check if extraction is enabled** — Go to Configuration → Custom → Extraction and verify your extractor is listed
4. **View a single page** — In Screaming Frog, right-click a URL → View Source. Search for your Post ID pattern manually.

### "Some pages have Post IDs, others don't"

- **Category/tag/archive pages** don't have Post IDs — they're dynamically generated, not stored as posts
- **Custom post types** might use different patterns
- This is normal. Screaming Fixes will skip pages without Post IDs and tell you why.

### "My theme doesn't output Post IDs anywhere"

Some heavily customized or headless WordPress setups strip this data. Options:

1. **Add shortlink support** — Add `add_theme_support('automatic-feed-links')` to your theme's functions.php
2. **Use a plugin** — Some SEO plugins restore the shortlink tag
3. **Manual CSV editing** — Export your posts from WordPress Admin (Tools → Export) which includes IDs, then merge with your Screaming Frog data

---

## Why This Matters

| Without Post IDs | With Post IDs |
|------------------|---------------|
| Manual lookups for each page | Instant identification |
| Fix 25 pages max (Quick Start Mode) | Fix unlimited pages (Full Mode) |
| Slower execution | 10x faster bulk updates |
| More API calls | Direct database targeting |

**5 minutes of setup = hours saved on every future project.**

---

## Need More Help?

- **Video walkthrough:** [Coming soon]
- **Screenshots:** [Coming soon]
- **Screaming Frog documentation:** [Custom Extraction Guide](https://www.screamingfrog.co.uk/seo-spider/user-guide/configuration/#custom-extraction)

---

*This guide is part of [Screaming Fixes](https://github.com/backofnapkin/screaming-fixes), a free open-source tool for bulk WordPress link fixing.*
