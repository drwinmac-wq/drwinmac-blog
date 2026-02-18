# Dr.WinMac Admin Dashboard — Phase 1

## Quick Start

1. **Login:** Open `login.html` and enter your admin passcode
2. **Write:** Enter a short post idea in the dashboard
3. **Expand:** Click "Expand with AI" to generate full article
4. **Review:** Check the AI-generated content in the preview
5. **Publish:** Click "Publish to Blog" to save and go live

## Files

- `login.html` — Passcode authentication page (client-side)
- `admin-dashboard.html` — Full publishing interface
- `admin_simple.html` — Older simple interface (deprecated, kept for reference)
- `admin_api_integration.js` — Helper utilities for API calls
- `drwinmac-blog-admin-v2.html` — Alternative admin interface (deprecated)

## How It Works

### Authentication

- Simple passcode stored in `.env` as `ADMIN_PASSCODE`
- Frontend stores passcode in `sessionStorage` (cleared on logout)
- All API calls require `Authorization: Bearer PASSCODE` header

### Expansion Workflow

1. **Input:** Short post (title + outline)
2. **AI Process:** GPT-4o expands using Dr.WinMac voice
3. **Email:** Preview sent to jeremy@drwinmac.tech
4. **Output:** Structured JSON with title, sections, teaser, image paths
5. **Publishing:** HTML file saved + blog index updated

### API Endpoints (All Require Auth)

```
POST /api/expand
  Body: { short_post: string, mode: 'smart'|'research'|'standard' }
  Response: { success, result: {...expanded post...}, email_sent, cost_estimate }

POST /api/publish
  Body: { post_data: {...} }
  Response: { success, filename, slug, index_updated }

GET /api/status
  Response: { engine_ready, openai_key_set, email_configured }

POST /api/test
  Response: { success, result, message }
```

## Environment Variables (Required)

In `.env`:

```
ADMIN_PASSCODE=YourSecurePasscode123
OPENAI_API_KEY=sk-xxx...
FROM_EMAIL=your-email@namecheap.com
SMTP_USERNAME=your-email@namecheap.com
SMTP_PASSWORD=your-email-password
SMTP_SERVER=mail.privateemail.com
SMTP_PORT=587
```

## Customization

Edit `admin-dashboard.html` to customize:

- Colors (CSS gradient: `#667eea` to `#764ba2`)
- Form fields (add more metadata if needed)
- Mode options (expansion modes)
- Button labels and messages

Edit `blog_api.py` to customize:

- HTML template structure (in `_generate_blog_html()`)
- Index update logic (in `_update_blog_index()`)
- Slug generation (in `_generate_slug()`)

## Security Notes

⚠️ **Important:**

- This is for **localhost development only** right now
- Passcode is transmitted in headers (use HTTPS in production)
- No rate limiting (add in Phase 2)
- No audit logging (add in Phase 3)

For production (Phase 2):

- Deploy to HTTPS-only
- Add rate limiting on login attempts
- Consider stronger auth (API keys instead of passcode)
- Log all publish actions
- Add approval workflows

---

**See `PHASE_1_SETUP.md` for full setup instructions and roadmap.**
