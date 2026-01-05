# Can't Find Your Post IDs? Custom Regex Guide

The default regex pattern works for most WordPress sites, but some themes store Post IDs differently. This guide will help you find your site's unique pattern.

## ⚠️ Important: Use the Right Page Type

**Post IDs only exist on individual posts and pages.** You will NOT find them on:
- ❌ Homepage
- ❌ Category pages (`/category/news/`)
- ❌ Tag pages (`/tag/recipes/`)
- ❌ Archive pages (`/2024/01/`)
- ❌ Author pages (`/author/john/`)
- ❌ Search results

**Always test on:**
- ✅ Individual blog posts (`/how-to-start-a-food-truck/`)
- ✅ Individual pages (`/about/`, `/contact/`)

## Why the Default Regex Might Not Work

The standard pattern looks for WordPress "shortlinks" like this:
```html
<link rel="shortlink" href="https://yoursite.com/?p=12345" />
```

But some sites:
- Have shortlinks disabled
- Use custom permalink structures
- Store Post IDs in different HTML elements
- Use page builders that add IDs elsewhere

## Option 1: Use AI to Find Your Pattern

This is the easiest method. You'll copy your page's HTML source and ask an AI to find where the Post ID is hidden.

### Step 1: Get Your Page Source

1. Go to any **individual blog post** on your WordPress site
   - ✅ Use: `yoursite.com/how-to-bake-bread/`
   - ❌ Don't use: Homepage, category pages, tag pages, or archives
2. Note the Post ID from WordPress admin (edit the post and look at the URL: `post.php?post=12345`)
3. On the live page, right-click → **View Page Source**
4. Press `Ctrl+A` (or `Cmd+A` on Mac) to select all
5. Press `Ctrl+C` to copy

### Step 2: Use This Prompt

Copy this prompt and paste it into Claude, ChatGPT, or any AI assistant:

---

**PROMPT TO COPY:**

```
I need help creating a custom regex pattern for Screaming Frog to extract WordPress Post IDs from my website's HTML.

Here's what I know:
- This page's Post ID is: [ENTER YOUR POST ID HERE, e.g., 12345]
- The regex needs to work in Screaming Frog's Custom Extraction feature (Regex type)
- The pattern should capture ONLY the numeric Post ID in a capture group

Here's the HTML source of my page:

[PASTE YOUR HTML SOURCE HERE]

Please:
1. Find where the Post ID appears in this HTML
2. Create a regex pattern that will extract it
3. Make sure the regex has exactly ONE capture group containing the Post ID number
4. Test that your regex would match and extract "12345" (or whatever my Post ID is)

Format your answer as:
- Where you found the Post ID: [location in HTML]
- Regex pattern: [the pattern]
- Explanation: [brief explanation of how it works]
```

---

### Step 3: Add to Screaming Frog

Once you have your custom regex:

1. In Screaming Frog, go to **Configuration → Custom → Extraction**
2. Click **Add** and set:
   - **Name:** `post_id`
   - **Type:** Regex
   - **Regex:** `[paste your custom regex here]`
3. Click **OK**
4. Re-crawl your site
5. Check **Custom Extraction** tab to verify Post IDs are being captured
6. Export via **Bulk Export → Custom Extraction → post_id**

## Option 2: Common Alternative Patterns

Here are regex patterns for common WordPress setups. Try these before creating a custom one:

### Pattern 1: Shortlink (Default)
```
<link[^>]+rel=['"]shortlink['"][^>]+href=['"][^'"]*\?p=(\d+)
```
*Looks for:* `<link rel="shortlink" href="...?p=12345" />`

### Pattern 2: Body Class
```
postid-(\d+)
```
*Looks for:* `<body class="post-template postid-12345 ...">`

### Pattern 3: Article ID
```
<article[^>]+id=['"]post-(\d+)['"]
```
*Looks for:* `<article id="post-12345" ...>`

### Pattern 4: Data Attribute
```
data-post-id=['"](\d+)['"]
```
*Looks for:* `<div data-post-id="12345" ...>`

### Pattern 5: WordPress JSON (REST API)
```
"postId":(\d+)
```
*Looks for:* Embedded JSON data with `"postId":12345`

### Pattern 6: Comment Form
```
<input[^>]+name=['"]comment_post_ID['"][^>]+value=['"](\d+)['"]
```
*Looks for:* Hidden input in comment forms

## Testing Your Regex

Before crawling your entire site:

1. In Screaming Frog, crawl just **5-10 pages**
2. Go to the **Custom Extraction** tab
3. Check that Post IDs appear for your blog posts
4. If most show numbers, you're good!
5. If empty, try a different pattern

## Still Stuck?

If none of these work:

1. **Check if Post IDs exist** - Some sites genuinely don't expose Post IDs in HTML
2. **Try the body class pattern** - This works on almost all WordPress themes
3. **Contact your theme developer** - Ask where Post IDs are stored
4. **Use the AI method above** - Share your full HTML and let AI find it

## Quick Reference

| Where to Look | What It Looks Like | Regex Pattern |
|---------------|-------------------|---------------|
| Shortlink | `<link rel="shortlink" href="?p=123">` | `\?p=(\d+)` |
| Body class | `class="postid-123"` | `postid-(\d+)` |
| Article tag | `<article id="post-123">` | `id=['"]post-(\d+)` |
| Data attribute | `data-post-id="123"` | `data-post-id=['"](\d+)` |
| JSON | `"postId":123` | `"postId":(\d+)` |

---

*Back to [Screaming Fixes](/) to upload your Post IDs*
