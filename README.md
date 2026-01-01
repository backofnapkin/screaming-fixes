# 🔧 Screaming Fixes

**Fix thousands of broken links and redirect chains in minutes, not hours.**

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://screaming-fixes.streamlit.app)
[![Built with Claude](https://img.shields.io/badge/AI-Claude_by_Anthropic-6B5CE7?logo=anthropic)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 The Problem

You run a Screaming Frog crawl and find **7,404 broken link references** and **thousands of redirect chains**. Now what?

Manually fixing each one means:
- Opening each WordPress post
- Finding the broken or outdated link in the content
- Deciding whether to remove or replace it
- Clicking publish
- Repeating hundreds of times

**Screaming Fixes automates this entire workflow.**

---

## ✨ Two Tools in One

### 🔗 Broken Links
Upload your Screaming Frog broken links export, review unique broken URLs, get AI suggestions for replacements, and apply fixes to WordPress.

### 🔄 Redirect Chains
Upload your redirect chains export, review outdated URLs that redirect to final destinations, and bulk-update them. No AI needed — the replacement URLs come directly from Screaming Frog.

---

## 🚀 How It Works

```
Upload CSV → Review Issues → Approve Fixes → Apply to WordPress
```

| Step | Broken Links | Redirect Chains |
|------|--------------|-----------------|
| **1. Upload** | Bulk Export → Response Codes → Client Error (4xx) → Inlinks | Reports → Redirects → All Redirects |
| **2. Review** | See 63 unique broken URLs (not 7,404 references) | See 307 unique redirects to update |
| **3. Decide** | Remove link, replace with new URL, or get AI suggestion | Approve replacement (final URL already known) |
| **4. Apply** | One click to fix all approved links via WordPress REST API | Same one-click workflow |

---

## 🚀 Two Modes

### 🤖 Agent Mode (Default)
- **Free to use** — no API key required
- 5 free AI suggestions per session (broken links only)
- Fixes up to 25 pages per session
- Auto-discovers WordPress Post IDs
- Perfect for testing and smaller sites

### 🚀 Enterprise Mode
- **Also free** — bring your own Claude API key
- Unlimited AI suggestions
- Unlimited page fixes
- Requires Post IDs in CSV (2-min Screaming Frog setup)
- Best for large sites with 100+ pages

---

## 🤖 AI-Powered Suggestions (Broken Links)

Claude analyzes each broken URL and recommends:

- **REMOVE** — Delete the hyperlink, keep the anchor text visible
- **REPLACE** — Swap with a working URL (found via web search)

**Example:**
```
Broken: https://example.com/old-franchise-guide/
AI Recommendation: REMOVE
Reason: Page was intentionally deleted. No similar content exists.
```

**You approve every suggestion before it's applied.**

---

## 🔄 Redirect Chains (No AI Needed)

Screaming Frog already knows where each redirect ends up. This tool simply:

1. Shows you which URLs on your site point to redirects
2. Tells you the final destination
3. Lets you approve the update
4. Applies fixes in bulk

**Example:**
```
Old URL: http://itunes.apple.com/us/podcast/...
Final URL: https://podcasts.apple.com/us/podcast/...
Action: Replace (approved)
```

**💡 Tip:** Not all redirects need fixing. Affiliate links and tracking URLs often redirect intentionally — use your judgment.

---

## 🔒 Privacy & Security

- ✅ All data processed in your browser session
- ✅ Nothing saved to any database
- ✅ WordPress credentials stored in session only
- ✅ Cleared when you close the tab
- ✅ Open source — inspect the code yourself

---

## ⚠️ Disclaimer

This tool is provided "as-is" without warranty of any kind. You are solely responsible for reviewing, approving, and applying any changes to your website. Screaming Frog data may occasionally contain errors or false positives. Always back up your site before making bulk changes. The creators of this tool are not liable for any damages or issues resulting from its use.

---

## 📦 Quick Start (Local)

```bash
# Clone
git clone https://github.com/backofnapkin/screaming-fixes.git
cd screaming-fixes

# Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure (optional - for AI suggestions)
cp .env.example .env
# Edit .env and add your AGENT_MODE_API_KEY

# Run
streamlit run app.py
```

### Export from Screaming Frog:

**For Broken Links:**
1. Run your site crawl
2. Go to **Bulk Export → Response Codes → Client Error (4xx) → Inlinks**
3. Upload the CSV to Screaming Fixes

**For Redirect Chains:**
1. Run your site crawl
2. Go to **Reports → Redirects → All Redirects**
3. Upload the CSV to Screaming Fixes

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| AI | Claude by Anthropic (with web search) |
| WordPress Integration | REST API + Application Passwords |
| Analytics | LangSmith (optional) |

---

## 📊 Smart Design Decisions

### Why NOT use AI for everything?

| Task | Uses AI? | Why |
|------|----------|-----|
| Post ID Discovery | ❌ No | HTTP requests are free and reliable |
| Link Replacement | ❌ No | WordPress REST API handles this |
| Redirect Chain Fixes | ❌ No | Final URLs already in CSV |
| Finding Replacement URLs | ✅ Yes | Web search + reasoning needed |
| Deciding Remove vs Replace | ✅ Yes | Context analysis required |

**Result:** AI costs ~$0.02-0.05 per suggestion, not per page fixed. Redirect chains cost nothing extra.

---

## 📁 Project Structure

```
screaming-fixes/
├── app.py                 # Main Streamlit application
├── wordpress_client.py    # WordPress REST API client
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── .streamlit/
│   └── config.toml       # Streamlit theme config
└── README.md
```

---

## 🔐 WordPress Setup

Screaming Fixes uses [Application Passwords](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/) (WordPress 5.6+):

1. Go to **WordPress Admin → Users → Profile**
2. Scroll to **Application Passwords**
3. Create one named "Screaming Fixes"
4. Copy the password (spaces are OK)

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Brett Lindenberg**  
Sr. Digital Marketing Strategist with 15+ years of SEO experience

- GitHub: [@backofnapkin](https://github.com/backofnapkin)
- Website: [backofnapkin.co](https://backofnapkin.co)

---

## 🙏 Acknowledgments

- [Screaming Frog](https://www.screamingfrog.co.uk/) for the excellent SEO spider
- [Anthropic](https://anthropic.com) for Claude AI
- [Streamlit](https://streamlit.io) for the rapid prototyping framework
