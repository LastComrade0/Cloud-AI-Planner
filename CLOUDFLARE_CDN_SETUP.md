# Cloudflare CDN Setup Guide

This guide will help you switch from CloudFront to Cloudflare CDN to meet the project requirements.

## Current Setup
- **S3 Bucket**: `cloud-ai-planner-frontend`
- **CloudFront Distribution**: Currently serving the site
- **Cloudflare DNS**: Gray cloud (DNS only, no proxy)

## Goal
- **Cloudflare CDN**: Orange cloud (proxied through Cloudflare)
- **Origin**: Keep CloudFront as origin (or switch to S3 directly)

---

## Step 1: Enable Cloudflare Proxy (Orange Cloud)

1. **Go to Cloudflare Dashboard**
   - Navigate to: https://dash.cloudflare.com
   - Select your domain: `simpleaiplanner.com`

2. **Go to DNS Settings**
   - Click **DNS** in the left sidebar
   - Find the DNS records for:
     - `www.simpleaiplanner.com` (CNAME or A record)
     - `simpleaiplanner.com` (A record, if exists)

3. **Enable Proxy**
   - For each record, click the **gray cloud icon** to turn it **orange**
   - Orange cloud = Proxied (CDN enabled)
   - Gray cloud = DNS only (no CDN)
   - **Important**: Enable proxy on `www` record (currently DNS only)
   - `simpleaiplanner.com` is already proxied ✅

4. **Verify Records**
   - `www.simpleaiplanner.com` should point to CloudFront: `d2pgi66z0m7yvm.cloudfront.net`
   - `simpleaiplanner.com` should point to CloudFront: `d2pgi66z0m7yvm.cloudfront.net`
   - Both should show **orange cloud** (proxied) after enabling

---

## Step 2: Configure SSL/TLS Settings

1. **Go to SSL/TLS Settings**
   - Click **SSL/TLS** in the left sidebar
   - Select **Overview** tab

2. **Set SSL/TLS Mode**
   - Choose **Full** mode (recommended for OAuth flows)
   - This ensures end-to-end encryption
   - Cloudflare encrypts to origin but doesn't validate the origin certificate
   - **Note**: Full (strict) can break OAuth redirects, so use **Full** mode

3. **If Using CloudFront as Origin**
   - CloudFront already has SSL, so **Full** mode works best
   - **Full (strict)** may cause issues with Google OAuth flows

4. **If Using S3 as Origin**
   - You may need to use **Flexible** mode initially
   - Or configure S3 with a custom domain and SSL certificate

---

## Step 3: Configure Origin Settings

### Option A: Keep CloudFront as Origin (Recommended)

**Why**: CloudFront is already working, so this is the safest option.

1. **In Cloudflare DNS**
   - Ensure `www.simpleaiplanner.com` CNAME points to your CloudFront domain
   - Example: `d1234567890.cloudfront.net`

2. **CloudFront Settings** (if needed)
   - In AWS CloudFront console, ensure your distribution accepts requests from Cloudflare IPs
   - Or use a custom header to verify requests come from Cloudflare

### Option B: Point Directly to S3

**Why**: Simpler architecture, but requires S3 static website hosting.

1. **Enable S3 Static Website Hosting**
   - Go to S3 bucket: `cloud-ai-planner-frontend`
   - Properties → Static website hosting → Enable
   - Note the website endpoint (e.g., `cloud-ai-planner-frontend.s3-website-us-west-1.amazonaws.com`)

2. **Update Cloudflare DNS**
   - Change `www.simpleaiplanner.com` CNAME to point to S3 website endpoint
   - Example: `cloud-ai-planner-frontend.s3-website-us-west-1.amazonaws.com`

3. **SSL/TLS Mode**
   - Use **Flexible** mode (S3 website endpoints don't support custom SSL)

---

## Step 4: Configure Cloudflare Settings

1. **Speed → Optimization**
   - Enable **Auto Minify** (HTML, CSS, JavaScript)
   - Enable **Brotli** compression

2. **Caching → Configuration**
   - Set **Caching Level**: Standard
   - **Browser Cache TTL**: 4 hours (or as needed)

3. **Security → DDoS Protection**
   - Should be **automatically enabled** when proxy is on
   - Verify it's active in Security → Overview

4. **Security → WAF (Web Application Firewall)**
   - Free tier includes basic WAF rules
   - Ensure it's enabled

---

## Step 5: Test the Setup

1. **Wait for DNS Propagation** (5-15 minutes)

2. **Test SSL**
   - Visit: https://www.simpleaiplanner.com
   - Check browser shows valid SSL certificate (Cloudflare certificate)

3. **Verify CDN is Working**
   - Open DevTools → Network tab
   - Reload the page
   - Check response headers:
     - Should see `cf-ray` header (Cloudflare CDN)
     - Should see `server: cloudflare` header

4. **Test Functionality**
   - Sign in with Google OAuth
   - Sign in with username/password
   - Upload a syllabus
   - Test all features

---

## Step 6: Troubleshooting

### SSL Handshake Failed
**Symptom**: Browser shows "SSL handshake failed" or "Connection refused"

**Solutions**:
1. Check SSL/TLS mode in Cloudflare:
   - If using CloudFront: Use **Full** mode (not Full strict)
   - If using S3: Use **Flexible** mode
2. Verify origin certificate is valid
3. Wait 5-10 minutes for changes to propagate

### OAuth Flow Not Working
**Symptom**: Google OAuth or other OAuth flows fail after selecting username

**Solutions**:
1. Change SSL/TLS mode from **Full (strict)** to **Full**
2. Full (strict) validates origin certificates and can break OAuth redirects
3. Full mode encrypts traffic but is more compatible with OAuth flows

### Site Not Loading
**Symptom**: Site shows error or doesn't load

**Solutions**:
1. Check DNS records point to correct origin
2. Verify origin (CloudFront/S3) is accessible
3. Check Cloudflare SSL/TLS mode matches your origin setup
4. Clear browser cache and try incognito mode

### CORS Errors
**Symptom**: API calls fail with CORS errors

**Solutions**:
1. Ensure `ALLOWED_ORIGINS` in Lambda includes `https://www.simpleaiplanner.com`
2. Verify API Gateway CORS settings
3. Check Cloudflare isn't blocking preflight requests (Security → WAF)

---

## Step 7: Optional - Remove CloudFront (After Testing)

Once Cloudflare CDN is working, you can optionally remove CloudFront to simplify:

1. **Point Cloudflare directly to S3**
   - Follow Option B in Step 3
   - Enable S3 static website hosting
   - Update DNS to point to S3 endpoint

2. **Delete CloudFront Distribution**
   - Go to AWS CloudFront console
   - Disable the distribution
   - Wait for it to be disabled
   - Delete the distribution

**Note**: Keep CloudFront if you want redundancy or specific AWS features.

---

## Verification Checklist

- [ ] DNS records show orange cloud (proxied)
- [ ] SSL/TLS mode is configured correctly
- [ ] Site loads at https://www.simpleaiplanner.com
- [ ] SSL certificate is valid (Cloudflare certificate)
- [ ] Response headers show `cf-ray` and `server: cloudflare`
- [ ] Authentication (Google + username/password) works
- [ ] API calls work without CORS errors
- [ ] DDoS protection is active in Cloudflare dashboard

---

## Next Steps

After Cloudflare CDN is working:
1. Add Cloudflare Turnstile (ReCaptcha alternative) to login forms
2. Verify DDoS protection is active
3. Update README.md with Cloudflare CDN setup instructions

