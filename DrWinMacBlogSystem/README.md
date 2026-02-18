# Dr.WinMac Blog Automation System

A production-ready, AI-powered blog publishing backend. Deploy live in 15 minutes.

Automatically expands short post ideas into full articles in your voice using GPT-4o. Password-protected admin dashboard. Saves HTML files and auto-updates your blog index.

**Perfect for:** Demonstrating automation infrastructure, personal showroom sites, and client workflows.

---

## ✨ Features

- 🚀 **Production-ready** — Deploy live immediately
- 🔐 **Secure authentication** — Passcode + rate limiting
- 🤖 **AI-powered expansion** — GPT-4o in your voice
- 📧 **Email previews** — Review before publishing
- 🎯 **Auto-publishing** — Saves HTML + updates blog index
- 💾 **No database** — File-based, zero infrastructure
- 📱 **Responsive UI** — Desktop & mobile
- 🔄 **Auto-deploy** — Push to GitHub → live in 2 minutes

---

## 🚀 Deploy Live (15 Minutes)

### Fastest: Render.com (Recommended)

1. **Push to GitHub**

   ```bash
   git add .
   git commit -m "Initial commit: Blog automation system"
   git push origin main
   ```

2. **Deploy on Render**

   - Go to [render.com](https://render.com)
   - Click "Create Web Service"
   - Connect your GitHub repo
   - Add environment variables (see `.env.example`)
   - Click "Deploy"

3. **Get live URL**
   - Render provides: `https://drwinmac-blog-api.onrender.com`
   - Update admin dashboard to point to this URL
   - Done!

**See `PRODUCTION_DEPLOY.md` for detailed steps.**

---

## 📖 How It Works

### Publishing Workflow

```
You write short post → AI expands (GPT-4o) → Email preview → Approve →
Published to /blog/ + index updated automatically
```

### Step-by-Step

1. **Login** — Enter passcode at `/admin/login.html`
2. **Write** — Short post idea (title + outline)
3. **Expand** — AI generates full article in your voice
4. **Review** — Check preview + receive email
5. **Publish** — One-click to save HTML + update blog index

### Output

- **Files:** `/blog/[slug].html` (complete blog post)
- **Index:** `/Blog/index.html` updated with new post card
- **Email:** Preview sent to configured recipient

---

## 🔧 API Endpoints

All endpoints require `Authorization: Bearer PASSCODE` header.

### Step-by-Step

1. **Login** (`/admin/login.html`) — Enter passcode
2. **Write** — Short post idea
3. **Expand** — AI generates full article
4. **Review** — Check content in preview
5. **Publish** — One-click save + index update

### API Endpoints

All endpoints require: `Authorization: Bearer YOUR_PASSCODE`

```bash
# Expand post
curl -X POST https://drwinmac-blog-api.onrender.com/api/expand \
  -H "Authorization: Bearer YourPasscode" \
  -H "Content-Type: application/json" \
  -d '{"short_post": "Your idea", "mode": "smart"}'

# Publish
curl -X POST https://drwinmac-blog-api.onrender.com/api/publish \
  -H "Authorization: Bearer YourPasscode" \
  -H "Content-Type: application/json" \
  -d '{"post_data": {...}}'

# Check status
curl https://drwinmac-blog-api.onrender.com/api/status \
  -H "Authorization: Bearer YourPasscode"
```

---

## 🔧 Configuration

### Environment Variables

Set these in your hosting provider (Render, Heroku, etc.):

| Variable              | Required | Example                  |
| --------------------- | -------- | ------------------------ |
| `OPENAI_API_KEY`      | ✅       | `sk-proj-...`            |
| `ADMIN_PASSCODE`      | ✅       | `MySecure123Pass`        |
| `FROM_EMAIL`          | ✅       | `you@namecheap.com`      |
| `SMTP_USERNAME`       | ✅       | `you@namecheap.com`      |
| `SMTP_PASSWORD`       | ✅       | `your-password`          |
| `SMTP_SERVER`         | ✅       | `mail.privateemail.com`  |
| `SMTP_PORT`           | ✅       | `587`                    |
| `CORS_ORIGINS`        | ✅       | `https://yourdomain.com` |
| `RATE_LIMIT_REQUESTS` | ❌       | `10` (default)           |
| `RATE_LIMIT_WINDOW`   | ❌       | `3600` (default)         |

---

## 📚 Documentation

| File                     | Purpose                    |
| ------------------------ | -------------------------- |
| **PRODUCTION_DEPLOY.md** | Deploy to Render in 15 min |
| **PHASE_1_SETUP.md**     | Detailed setup guide       |
| **GITHUB_SETUP.md**      | Push to GitHub             |
| **admin/README.md**      | Admin dashboard docs       |

---

## 🔐 Production Security

✅ **Included:**

- HTTPS required (handled by Render)
- Rate limiting (10 requests per hour per IP)
- Passcode authentication
- Structured logging
- Health checks

✅ **You should:**

- Use strong passcode (12+ chars)
- Never commit `.env`
- Restrict CORS to your domain
- Monitor logs in Render dashboard
- Rotate OPENAI_API_KEY quarterly

---

## 🚨 Troubleshooting

### "502 Bad Gateway" on Render

- Check logs: Render dashboard → Logs
- Verify all env vars are set
- Check OPENAI_API_KEY validity

### Email not sending

- Verify SMTP credentials
- Check if provider requires app password
- Review logs for SMTP errors

### Rate limit blocking requests

- Check client IP in logs
- Increase RATE_LIMIT_REQUESTS if needed
- Contact provider if attack suspected

---

## 💡 What's Next?

- ✅ **Phase 1:** Core system (complete)
- ✅ **Phase 2:** Production deployment (Render ready)
- 📅 **Phase 3:** Scheduling & approval workflows
- 📅 **Phase 4:** Custom forms + email automation
- 📅 **Phase 5:** Client scalability

---

## 📄 License

Personal use. Modify as needed for your site.

---

**Production-ready. Deploy now. 🚀**
