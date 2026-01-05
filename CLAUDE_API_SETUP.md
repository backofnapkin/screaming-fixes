# How to Get Your Claude API Key

This guide walks you through setting up a Claude API key to enable AI-powered suggestions in Screaming Fixes.

## What You'll Get

With a Claude API key, you can:
- Get AI suggestions for broken link fixes (remove vs replace)
- Auto-generate alt text for images by analyzing the actual image
- Save hours of manual research

## What It Costs

- **Free to start**: New accounts get $5 in free credits
- **Pay as you go**: ~$0.003-0.01 per suggestion (typically pennies)
- **No monthly fee**: Only pay for what you use
- **Typical usage**: Fixing 100 broken links costs roughly $0.50-1.00

## Step-by-Step Setup

### Step 1: Create an Anthropic Account

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Click **Sign Up**
3. Enter your email and create a password
4. Verify your email address

### Step 2: Add Billing (Required for API Access)

Even though you get free credits, Anthropic requires a payment method:

1. Once logged in, click **Settings** (gear icon) in the left sidebar
2. Click **Billing**
3. Click **Add Payment Method**
4. Enter your credit card details
5. Set a **Usage Limit** to control spending (e.g., $10/month)

> 💡 **Tip:** Set a low usage limit like $5-10/month. You can always increase it later. This prevents any surprise charges.

### Step 3: Generate Your API Key

1. In the left sidebar, click **API Keys**
2. Click **Create Key**
3. Give it a name like `Screaming Fixes`
4. Click **Create Key**
5. **Copy the key immediately** - you won't be able to see it again!

### What Your API Key Looks Like

Your key will look something like this:
```
sk-ant-api03-aBcDeFgHiJkLmNoPqRsTuVwXyZ123456789...
```

Key characteristics:
- Starts with `sk-ant-api03-`
- About 100+ characters long
- Mix of letters and numbers
- Case-sensitive (copy it exactly)

> ⚠️ **Keep it secret!** Your API key is like a password. Don't share it publicly or commit it to GitHub.

## Adding Your Key to Screaming Fixes

1. In Screaming Fixes, go to **Complete Integrations Setup**
2. Find **Step 2: Add Your AI API Key**
3. Paste your key in the input field
4. Click **Save API Key**

That's it! You're ready to use AI-powered suggestions.

## Troubleshooting

### "Invalid API Key" Error
- Make sure you copied the entire key (it's long!)
- Check for extra spaces before or after the key
- Verify the key starts with `sk-ant-`

### "Insufficient Credits" Error
- Add a payment method in Anthropic Console
- Check your usage limits aren't set to $0

### "Rate Limit" Error
- You're making too many requests too quickly
- Wait a few seconds and try again
- This is rare with normal usage

## Managing Your Usage

To monitor your API spending:

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Click **Usage** in the left sidebar
3. See your daily/monthly usage and costs

### Setting Spending Limits

1. Go to **Settings** → **Billing**
2. Under **Usage Limits**, set:
   - **Monthly limit**: Maximum spend per month
   - **Daily limit**: Maximum spend per day (optional)

## Security Best Practices

- ✅ Set a reasonable usage limit ($5-20/month for most users)
- ✅ Use a unique API key for Screaming Fixes
- ✅ Regenerate your key if you think it's been exposed
- ❌ Don't share your key with others
- ❌ Don't post your key in public forums or GitHub

## FAQ

**Q: Is the API key the same as my Anthropic login password?**
No! Your API key is separate from your account password. The API key is specifically for programmatic access.

**Q: Can I use the free Claude.ai chat instead?**
No, the free chat interface doesn't provide API access. You need an API key from console.anthropic.com.

**Q: What model does Screaming Fixes use?**
We use Claude Sonnet 4, which offers the best balance of quality and cost for SEO tasks.

**Q: Will you store my API key?**
No. Your API key is stored only in your browser session and is never sent to our servers. When you close the tab, it's gone.

---

*Back to [Screaming Fixes](/) to continue setup*
