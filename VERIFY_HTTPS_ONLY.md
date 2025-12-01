# Verify HTTPS Only Access

This guide will help you verify that your site only allows HTTPS access (no HTTP).

## Requirement
"SSL enabled (HTTPS only access)" - All traffic must use HTTPS, HTTP should be blocked or redirected.

## Method 1: Test HTTP Access (Should Redirect to HTTPS)

### Test in Browser
1. **Try accessing HTTP version**
   - Visit: `http://www.simpleaiplanner.com` (note: `http://` not `https://`)
   - **Expected**: Should automatically redirect to `https://www.simpleaiplanner.com`

2. **Check the URL bar**
   - After redirect, URL should show `https://` (with padlock icon)
   - Should NOT stay on `http://`

### Test with curl/PowerShell
```powershell
# Test HTTP request
Invoke-WebRequest -Uri "http://www.simpleaiplanner.com" -MaximumRedirection 0 -ErrorAction SilentlyContinue
```

**Expected**: Should get redirect (301 or 302) to HTTPS

## Method 2: Check Cloudflare Settings

1. **Go to Cloudflare Dashboard**
   - Navigate to: https://dash.cloudflare.com
   - Select your domain: `simpleaiplanner.com`

2. **Go to SSL/TLS → Edge Certificates**
   - Click **SSL/TLS** → **Edge Certificates**
   - Look for **"Always Use HTTPS"**
   - Should be **Enabled** ✅

3. **If Not Enabled:**
   - Toggle **"Always Use HTTPS"** to **ON**
   - This automatically redirects all HTTP to HTTPS

## Method 3: Check CloudFront Settings (If Applicable)

If you're using CloudFront as origin:

1. **Go to AWS CloudFront Console**
   - Navigate to: https://console.aws.amazon.com/cloudfront/
   - Select your distribution

2. **Check Viewer Protocol Policy**
   - Go to **Behaviors** tab
   - Click on the behavior
   - **Viewer Protocol Policy** should be:
     - **Redirect HTTP to HTTPS** ✅ (recommended)
     - Or **HTTPS Only** ✅

## Method 4: Test with Browser DevTools

1. **Open DevTools (F12)**
2. **Go to Network tab**
3. **Try accessing HTTP version**
   - Type: `http://www.simpleaiplanner.com` in address bar
   - Press Enter

4. **Check Network Tab**
   - Should see a redirect (301 or 302)
   - Final request should be to `https://www.simpleaiplanner.com`

## Method 5: Check Response Headers

1. **Test HTTP request**
   - Use curl or browser DevTools
   - Request: `http://www.simpleaiplanner.com`

2. **Check Response Headers**
   - Should see: `Location: https://www.simpleaiplanner.com`
   - Status code: `301` (Permanent Redirect) or `302` (Temporary Redirect)

## Method 6: Verify No HTTP Content

1. **Check for Mixed Content**
   - Open your site: `https://www.simpleaiplanner.com`
   - Open DevTools (F12) → Console tab
   - Look for warnings about:
     - Mixed content (HTTP resources on HTTPS page)
     - Insecure resources

2. **Should NOT see:**
   - HTTP URLs in page source
   - Mixed content warnings
   - Insecure resource warnings

## Expected Results

### ✅ HTTPS Only is Working If:
- HTTP requests redirect to HTTPS (301/302)
- Cloudflare "Always Use HTTPS" is enabled
- Browser shows padlock icon (HTTPS)
- No mixed content warnings

### ❌ HTTPS Only is NOT Working If:
- HTTP requests don't redirect
- Site is accessible via HTTP
- Mixed content warnings appear
- "Always Use HTTPS" is disabled

## Quick Test

**Easiest way to test:**
1. Open a new incognito/private window
2. Type: `http://www.simpleaiplanner.com` (note: `http://`)
3. Press Enter
4. **Should automatically redirect to `https://www.simpleaiplanner.com`**
5. URL bar should show padlock icon 🔒

## Cloudflare Configuration

If "Always Use HTTPS" is not enabled:

1. **Go to SSL/TLS → Edge Certificates**
2. **Toggle "Always Use HTTPS" to ON**
3. **Save**
4. **Test again** - HTTP should now redirect to HTTPS

## Summary

**To verify HTTPS only access:**
1. ✅ Test HTTP redirects to HTTPS
2. ✅ Check Cloudflare "Always Use HTTPS" is enabled
3. ✅ Verify no mixed content warnings
4. ✅ Confirm padlock icon in browser

