# Testing Cloudflare Bot Protection / CAPTCHA

This guide will help you verify that Cloudflare's Bot Fight Mode and CAPTCHA challenges are actually working.

## Method 1: Use Bot Detection Testing Tool (Easiest)

1. **Visit Bot Detection Test Site**
   - Go to: https://bot.sannysoft.com/
   - This site tests if Cloudflare protection is active

2. **What to Look For**
   - Should detect Cloudflare protection
   - Should show Cloudflare headers
   - Should indicate bot protection is active

## Method 2: Simulate Bot Traffic with curl

Test if Cloudflare challenges suspicious requests:

### Test 1: Normal Request (Should Work)
```bash
curl -I https://www.simpleaiplanner.com
```

**Expected**: Should return 200 OK with Cloudflare headers

### Test 2: Bot-like Request (May Trigger Challenge)
```bash
curl -I -H "User-Agent: bot" https://www.simpleaiplanner.com
```

**Expected**: May return 403 or challenge page if bot protection is strict

### Test 3: Missing User-Agent (Suspicious)
```bash
curl -I -H "User-Agent: " https://www.simpleaiplanner.com
```

**Expected**: May trigger challenge or be blocked

## Method 3: Check Cloudflare Analytics

1. **Go to Cloudflare Dashboard**
   - Navigate to: https://dash.cloudflare.com
   - Select your domain: `simpleaiplanner.com`

2. **Check Security → Events**
   - Click **Security** → **Events** (or **Analytics** → **Security**)
   - Look for:
     - Bot events
     - Challenge events
     - Blocked requests

3. **Check Bot Analytics**
   - Go to **Security** → **Bots**
   - Click **View bot events**
   - Should show bot traffic statistics

## Method 4: Use Browser with Suspicious Behavior

1. **Disable JavaScript** (temporarily)
   - Open DevTools (F12)
   - Go to Settings → Preferences → Debugger
   - Check "Disable JavaScript"
   - Reload the page

2. **What Should Happen**
   - Cloudflare may show a challenge page
   - Or the page may not load properly (since your site needs JS)

3. **Re-enable JavaScript** after testing

## Method 5: Use VPN or Tor Browser

1. **Connect via VPN** or use Tor Browser
2. **Visit your site**: `https://www.simpleaiplanner.com`
3. **What Should Happen**
   - May see a Cloudflare challenge page
   - May need to complete a CAPTCHA
   - This proves bot protection is working

## Method 6: Check Response Headers

1. **Open your site in browser**
   - Visit: `https://www.simpleaiplanner.com`
   - Open DevTools (F12) → Network tab
   - Reload the page

2. **Check Response Headers**
   - Click on the main request
   - Look for these headers:
     - `cf-ray` - Cloudflare CDN (should be present)
     - `server: cloudflare` - Cloudflare is serving (should be present)
     - `cf-bot-score` - Bot score (if available)
     - `cf-threat-score` - Threat score (if available)
     - `cf-mitigated` - If request was mitigated

## Method 7: Test with Automated Tool

Use a tool that simulates bot behavior:

### Using Python (if you have it installed)
```python
import requests

# Test 1: Normal request
response = requests.get('https://www.simpleaiplanner.com')
print(f"Status: {response.status_code}")
print(f"Server: {response.headers.get('server', 'Not found')}")
print(f"CF-Ray: {response.headers.get('cf-ray', 'Not found')}")

# Test 2: Bot-like request
headers = {
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
}
response = requests.get('https://www.simpleaiplanner.com', headers=headers)
print(f"\nBot-like request Status: {response.status_code}")
```

## Method 8: Check Cloudflare Firewall Events

1. **Go to Cloudflare Dashboard**
   - Click **Security** → **Events** (or **WAF** → **Events**)
   - Look for recent events

2. **What to Look For**
   - Bot challenges
   - Blocked requests
   - Challenge pages shown

## Expected Results

### ✅ Bot Protection is Working If:
- Bot detection test site shows Cloudflare protection
- Cloudflare Analytics shows bot events
- Suspicious requests trigger challenges or blocks
- Response headers include Cloudflare headers

### ❌ Bot Protection May Not Be Working If:
- No Cloudflare headers in responses
- Bot detection test doesn't show Cloudflare
- No bot events in Cloudflare Analytics
- Suspicious requests don't trigger challenges

## Quick Test (Recommended)

**Easiest way to test:**

1. **Visit**: https://bot.sannysoft.com/
2. **Check if it detects Cloudflare**
3. **Visit your site from that page** and see if it shows Cloudflare protection

## Alternative: Trigger a Challenge Manually

If you want to see a challenge page:

1. **Use a VPN** or **Tor Browser**
2. **Visit your site** multiple times quickly
3. **Cloudflare may show a challenge page** to verify you're human

## Note

Cloudflare's Bot Fight Mode is **intelligent** - it doesn't challenge every request. It:
- Challenges suspicious traffic
- Blocks known malicious bots
- Allows legitimate traffic through

So you may not see challenges on normal browsing, but protection is still active.

