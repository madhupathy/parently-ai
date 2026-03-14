# Parently — Deployment Guide

Complete step-by-step guide to deploy Parently on Railway, connect your LLM accounts, and publish to the Google Play Store and Apple App Store as a PWA.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Set up Neon Postgres](#2-set-up-neon-postgres)
3. [Get your LLM API keys](#3-get-your-llm-api-keys)
4. [Set up Google OAuth](#4-set-up-google-oauth)
5. [Set up Stripe billing](#5-set-up-stripe-billing)
6. [Deploy backend to Railway](#6-deploy-backend-to-railway)
7. [Deploy frontend to Railway](#7-deploy-frontend-to-railway)
8. [Set up cron jobs](#8-set-up-cron-jobs)
9. [Verify everything works](#9-verify-everything-works)
10. [Make it a PWA (Progressive Web App)](#10-make-it-a-pwa)
11. [Publish to Google Play Store](#11-publish-to-google-play-store)
12. [Publish to Apple App Store](#12-publish-to-apple-app-store)
13. [Custom domain (optional)](#13-custom-domain-optional)

---

## 1. Prerequisites

You will need accounts on these services (all have free tiers):

| Service | Purpose | Sign up |
|---|---|---|
| **Railway** | Hosting (backend + frontend) | https://railway.app |
| **Neon** | Postgres database + pgvector | https://neon.tech |
| **Google Cloud** | OAuth login + Gmail API | https://console.cloud.google.com |
| **Google AI Studio** | Gemini 1.5 Flash API key | https://aistudio.google.com |
| **Stripe** | Billing ($3/mo premium plan) | https://dashboard.stripe.com |
| **GitHub** | Source code hosting | https://github.com |

Optional:
| Service | Purpose | Sign up |
|---|---|---|
| **OpenAI** | Fallback LLM (GPT-4o-mini) | https://platform.openai.com |
| **Google Play Console** | Android app store listing | https://play.google.com/console ($25 one-time) |
| **Apple Developer** | iOS app store listing | https://developer.apple.com ($99/year) |

### Push code to GitHub

```bash
cd /home/dell/parently
git init
git add -A
git commit -m "Initial commit"
git remote add origin git@github.com:YOUR_USERNAME/parently.git
git push -u origin main
```

---

## 2. Set up Neon Postgres

1. Go to https://console.neon.tech → **New Project**
2. Name: `parently`, Region: pick closest to your users (e.g. `us-east-2`)
3. Copy the **connection string** — it looks like:
   ```
   postgresql://parently:AbCdEf123@ep-cool-name-123456.us-east-2.aws.neon.tech/parently?sslmode=require
   ```
4. Enable the **pgvector** extension:
   - Go to your project → **SQL Editor**
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`

> Save the connection string — you'll need it as `BACKEND_DATABASE_URL` in Railway.

---

## 3. Get your LLM API keys

### Gemini 1.5 Flash (primary — free tier available)

1. Go to https://aistudio.google.com/app/apikey
2. Click **Create API key** → select your Google Cloud project (or create one)
3. Copy the key — looks like `AIzaSy...`

> Save as `GEMINI_API_KEY`

### OpenAI (optional fallback)

1. Go to https://platform.openai.com/api-keys
2. Click **Create new secret key**
3. Copy the key — looks like `sk-proj-...`

> Save as `OPENAI_API_KEY`. This is optional — Gemini is the primary LLM. OpenAI is only used if Gemini is unavailable.

---

## 4. Set up Google OAuth

This enables "Continue with Google" login and Gmail API access.

1. Go to https://console.cloud.google.com/apis/credentials
2. **Create Project** (if you don't have one) → name it `Parently`
3. **OAuth consent screen**:
   - User Type: **External**
   - App name: `Parently`
   - Support email: your email
   - Authorized domains: add your Railway domain later (e.g. `parently-web.up.railway.app`)
   - Scopes: add `email`, `profile`, `openid`
   - For Gmail access, also add: `https://www.googleapis.com/auth/gmail.readonly`
4. **Create OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Name: `Parently Web`
   - **Authorized JavaScript origins**:
     ```
     https://parently-web.up.railway.app
     http://localhost:3001
     ```
   - **Authorized redirect URIs**:
     ```
     https://parently-web.up.railway.app/api/auth/callback/google
     http://localhost:3001/api/auth/callback/google
     ```
5. Copy **Client ID** and **Client Secret**

> Save as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

---

## 5. Set up Stripe billing

1. Go to https://dashboard.stripe.com → sign up / log in
2. **Create a Product**:
   - Go to **Products** → **Add product**
   - Name: `Parently Premium`
   - Price: **$3.00 / month** (recurring)
   - Click **Save**
   - Copy the **Price ID** (starts with `price_...`)
3. **Get API keys**:
   - Go to **Developers** → **API keys**
   - Copy the **Secret key** (starts with `sk_test_...` or `sk_live_...`)
4. **Set up webhook** (do this after deploying backend):
   - Go to **Developers** → **Webhooks** → **Add endpoint**
   - URL: `https://parently-api.up.railway.app/api/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copy the **Webhook signing secret** (starts with `whsec_...`)

> Save as `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, and `STRIPE_WEBHOOK_SECRET`

---

## 6. Deploy backend to Railway

1. Go to https://railway.app → **New Project** → **Deploy from GitHub repo**
2. Select your `parently` repository
3. Railway will detect the repo. Click **Add a Service** → configure:

### Backend service settings

- **Root Directory**: `apps/backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port $PORT`

### Backend environment variables

Go to the service → **Variables** → **Raw Editor** and paste:

```env
# Database
BACKEND_DATABASE_URL=postgresql://parently:YOUR_PASSWORD@ep-xxx.us-east-2.aws.neon.tech/parently?sslmode=require

# Auth (generate a random 32+ char string — MUST match frontend)
NEXTAUTH_SECRET=generate-a-random-secret-string-here-at-least-32-chars

# LLM
GEMINI_API_KEY=AIzaSy...your-gemini-key
GEMINI_MODEL=gemini-1.5-flash
OPENAI_API_KEY=sk-proj-...your-openai-key
OPENAI_MODEL=gpt-4o-mini

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

# CORS (your frontend Railway URL)
ALLOWED_ORIGINS=https://parently-web.up.railway.app

# Cron (generate another random secret)
CRON_SECRET=generate-another-random-secret-here

# Storage
DATA_DIR=./data
PDF_FOLDER=./uploads
```

4. Click **Deploy** → wait for the build to complete
5. Go to **Settings** → **Networking** → **Generate Domain** (e.g. `parently-api.up.railway.app`)
6. Test: visit `https://parently-api.up.railway.app/healthz` — should return `{"ok": true}`

---

## 7. Deploy frontend to Railway

1. In the same Railway project, click **New Service** → **Deploy from GitHub repo** (same repo)

### Frontend service settings

- **Root Directory**: `apps/web`
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm run start`

### Frontend environment variables

```env
# Backend URL (use Railway's internal networking for speed)
BACKEND_URL=http://parently-api.railway.internal:PORT
# Or use the public URL:
# BACKEND_URL=https://parently-api.up.railway.app

# Auth (MUST match backend)
NEXTAUTH_SECRET=same-secret-as-backend

# Frontend URL
NEXTAUTH_URL=https://parently-web.up.railway.app

# Google OAuth
GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
```

2. Click **Deploy**
3. Go to **Settings** → **Networking** → **Generate Domain** (e.g. `parently-web.up.railway.app`)
4. Test: visit `https://parently-web.up.railway.app` — you should see the landing page

> **Important**: Go back to Google Cloud Console and add your Railway frontend domain to the OAuth authorized origins and redirect URIs.

---

## 8. Set up cron jobs

Railway supports scheduled tasks via cron triggers.

1. In your Railway project, click **New Service** → **Cron Job**
2. Create **two** cron triggers:

### Daily digest cron (6am Central)

- **Schedule**: `0 12 * * *` (6am CST = 12:00 UTC)
- **Command**:
  ```bash
  curl -X POST https://parently-api.up.railway.app/api/internal/run-daily-digests \
    -H "X-Cron-Secret: your-cron-secret-here"
  ```

### School source refresh cron (4am Central)

- **Schedule**: `0 10 * * *` (4am CST = 10:00 UTC)
- **Command**:
  ```bash
  curl -X POST https://parently-api.up.railway.app/api/internal/refresh-school-sources \
    -H "X-Cron-Secret: your-cron-secret-here"
  ```

> **Alternative**: Use Railway's built-in cron service or an external cron service like https://cron-job.org (free).

---

## 9. Verify everything works

Run through this checklist:

- [ ] Visit `https://parently-api.up.railway.app/healthz` → returns `{"ok": true}`
- [ ] Visit `https://parently-web.up.railway.app` → landing page loads with FAQ
- [ ] Click **Continue with Google** → Google OAuth flow works
- [ ] Complete onboarding → enter child name + school
- [ ] School discovery runs → sources appear on step 3
- [ ] Click **Go to Dashboard** → dashboard loads
- [ ] Click **Run Digest** → digest generates successfully
- [ ] Go to **Settings** → integrations show Gmail + Google Drive only
- [ ] Click **Pricing** → upgrade flow works (use Stripe test card `4242 4242 4242 4242`)
- [ ] Click 🏠 Parently logo → navigates back to home page

---

## 10. Make it a PWA

Parently is **already fully configured** as a Progressive Web App. The following are wired into the codebase:

### What's already in place

| Item | File | Status |
|---|---|---|
| **PWA manifest** | `public/manifest.json` | ✅ name, icons, screenshots, orientation, display |
| **App icons** | `public/icons/icon-192.png`, `icon-512.png` | ✅ generated from SVG source |
| **Layout meta tags** | `app/layout.tsx` | ✅ manifest link, apple-mobile-web-app, viewport, theme-color |
| **Safe area CSS** | `app/globals.css` | ✅ iOS notch/home indicator padding |
| **Bottom tab bar** | `components/mobile-nav.tsx` | ✅ 5-tab native-style nav (mobile only) |
| **Touch optimization** | `app/layout.tsx` body class | ✅ `touch-manipulation` |
| **Standalone output** | `next.config.mjs` | ✅ `output: "standalone"` |

### Before publishing — create these content assets

- **`public/screenshots/screenshot-wide.png`** (1280×720) — desktop install prompt
- **`public/screenshots/screenshot-narrow.png`** (390×844) — mobile install prompt

> **Tip**: Take actual screenshots of your deployed app. Use https://www.pwabuilder.com/imageGenerator for additional icon sizes if needed.

### Test PWA

1. Deploy to Railway (or run locally with HTTPS)
2. Open in Chrome → you should see an **Install** prompt in the address bar
3. On iOS Safari: tap **Share** → **Add to Home Screen**
4. The app opens fullscreen with the bottom nav bar — feels native

---

## 11. Publish to Google Play Store

Google Play supports **TWA (Trusted Web Activity)** — a way to wrap your PWA as an Android app with no native code.

### Step 1: Set up Android Studio

1. Install [Android Studio](https://developer.android.com/studio)
2. Install Java JDK 17+

### Step 2: Use PWABuilder (easiest method)

1. Go to https://www.pwabuilder.com
2. Enter your URL: `https://parently-web.up.railway.app`
3. Click **Start** → it will analyze your PWA
4. Click **Package for stores** → **Android** → **Download**
5. This gives you a ready-to-sign APK/AAB

### Step 3: Use Bubblewrap (manual method)

```bash
npm install -g @nicolo-ribaudo/bubblewrap

bubblewrap init --manifest=https://parently-web.up.railway.app/manifest.json
# Follow prompts:
#   - Application ID: com.parently.app
#   - App name: Parently
#   - Launcher name: Parently
#   - Theme color: #6366f1
#   - Background color: #ffffff

bubblewrap build
# Outputs: app-release-signed.aab
```

### Step 4: Digital Asset Links (required!)

This proves you own both the domain and the app. The file already exists at:
`apps/web/public/.well-known/assetlinks.json`

Update it with your signing key fingerprint:
```bash
keytool -list -v -keystore your-keystore.jks -alias your-alias | grep SHA256
```

### Step 5: Publish to Google Play

1. Go to https://play.google.com/console → **Create app**
2. Fill in app details:
   - Name: **Parently**
   - Category: **Parenting**
   - Description: "AI-powered daily school digest. Consolidates Gmail, school calendars, ClassDojo, Brightwheel, and more into a calm 1-minute morning brief."
3. Upload your AAB from step 3
4. Add screenshots (phone + tablet + feature graphic)
5. Complete **Content rating** questionnaire
6. Set **Pricing**: Free
7. Submit for review → typically 1-3 days

> **Cost**: $25 one-time Google Play Console registration fee.

---

## 12. Publish to Apple App Store

Apple doesn't support TWA natively, but you have two options:

### Option A: PWABuilder (recommended, easiest)

1. Go to https://www.pwabuilder.com
2. Enter your URL: `https://parently-web.up.railway.app`
3. Click **Package for stores** → **iOS** → **Download**
4. This generates an Xcode project with a WKWebView wrapper
5. Open in Xcode, set your signing team, build, and submit

### Option B: Manual WKWebView wrapper

1. Open **Xcode** → **New Project** → **iOS App**
2. Name: `Parently`, Bundle ID: `com.parently.app`
3. Replace the main view with a WKWebView pointing to your URL:

```swift
import SwiftUI
import WebKit

struct ContentView: View {
    var body: some View {
        WebView(url: URL(string: "https://parently-web.up.railway.app/dashboard")!)
            .edgesIgnoringSafeArea(.all)
    }
}

struct WebView: UIViewRepresentable {
    let url: URL
    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.load(URLRequest(url: url))
        return webView
    }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
```

4. Add to `Info.plist`:
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <false/>
</dict>
```

### Submit to App Store

1. Go to https://appstoreconnect.apple.com → **My Apps** → **+** → **New App**
2. Fill in:
   - Name: **Parently**
   - Primary language: English
   - Bundle ID: `com.parently.app`
   - SKU: `parently-001`
   - Category: **Lifestyle** or **Education**
3. Upload screenshots:
   - 6.7" (iPhone 15 Pro Max): 1290 x 2796
   - 6.5" (iPhone 14 Plus): 1284 x 2778
   - 12.9" iPad Pro: 2048 x 2732
4. Description:
   > "Parently gives busy parents a calm 1-minute daily brief instead of 50 school emails. Connects to Gmail, auto-discovers your school's calendar and website, and intelligently parses emails from ClassDojo, Brightwheel, Skyward, and Kumon. Add your kids, and we handle the rest."
5. Keywords: `school, parent, digest, email, calendar, classdojo, brightwheel, education`
6. In Xcode: **Product** → **Archive** → **Distribute App** → **App Store Connect**
7. Back in App Store Connect: select the build, submit for review

> **Cost**: $99/year Apple Developer Program membership.
> **Review time**: Typically 1-2 days. Apple may ask you to justify the WKWebView approach — explain it's a PWA with offline support.

---

## 13. Custom domain (optional)

Instead of `parently-web.up.railway.app`, use your own domain.

1. Buy a domain (e.g. `parently.app` from Google Domains or Namecheap)
2. In Railway: **Frontend service** → **Settings** → **Networking** → **Custom Domain** → enter `app.parently.app`
3. Add the DNS records Railway gives you (typically a CNAME)
4. Update these values everywhere:
   - `NEXTAUTH_URL=https://app.parently.app`
   - `ALLOWED_ORIGINS=https://app.parently.app`
   - Google OAuth authorized origins + redirect URIs
   - Stripe webhook URL
   - `manifest.json` start_url
   - Digital Asset Links file

---

## Quick Reference: All Environment Variables

### Backend

| Variable | Example | Where to get it |
|---|---|---|
| `BACKEND_DATABASE_URL` | `postgresql://...` | Neon dashboard |
| `NEXTAUTH_SECRET` | `my-super-secret-32chars` | Generate: `openssl rand -hex 32` |
| `GEMINI_API_KEY` | `AIzaSy...` | https://aistudio.google.com/app/apikey |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Default |
| `OPENAI_API_KEY` | `sk-proj-...` | https://platform.openai.com/api-keys |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default |
| `STRIPE_SECRET_KEY` | `sk_live_...` | Stripe dashboard → API keys |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Stripe dashboard → Webhooks |
| `STRIPE_PRICE_ID` | `price_...` | Stripe dashboard → Products |
| `ALLOWED_ORIGINS` | `https://app.parently.app` | Your frontend URL |
| `CRON_SECRET` | `my-cron-secret` | Generate: `openssl rand -hex 16` |

### Frontend

| Variable | Example | Where to get it |
|---|---|---|
| `BACKEND_URL` | `https://parently-api.up.railway.app` | Railway backend URL |
| `NEXTAUTH_SECRET` | (same as backend) | Must match |
| `NEXTAUTH_URL` | `https://app.parently.app` | Your frontend URL |
| `GOOGLE_CLIENT_ID` | `123...googleusercontent.com` | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` | Google Cloud Console |

---

## Estimated Costs

| Item | Cost |
|---|---|
| Railway (Hobby plan) | $5/month |
| Neon Postgres (free tier) | $0 |
| Gemini API (free tier: 60 RPM) | $0 |
| Stripe (2.9% + $0.30 per charge) | Per transaction |
| Google Play Console | $25 one-time |
| Apple Developer Program | $99/year |
| Custom domain | ~$12/year |
| **Total to launch** | **~$5/month + store fees** |
