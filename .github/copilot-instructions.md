# Dr.WinMac Copilot Instructions

## Project Overview

This is a two-part system:

1. **Static website** (`/`) — A local tech services site (computer repair, Denver) built with plain HTML + a single shared `styles.css`. Deployed to Namecheap hosting via FTP on every push to `main`.
2. **Blog automation API** (`DrWinMacBlogSystem/`) — A Flask backend deployed separately on Render.com that expands short post ideas into full blog articles using GPT-4o, then commits them to this GitHub repo to trigger the static site deployment.

## Architecture & Data Flow

```
Admin writes short idea → POST /api/expand (Render API) → GPT-4o expansion
→ POST /api/publish → HTML file + metadata.json written to /blog/
→ GitHub API commits blog/[slug].html + blog/index.html + blog/metadata.json
→ workflow_dispatch triggers deploy.yml → FTP deploy to Namecheap → live
```

Key files:

- `DrWinMacBlogSystem/engine.py` — GPT-4o expansion with a hardcoded voice profile (calm, observational, no hype)
- `DrWinMacBlogSystem/publishing.py` — `BlogPublisher`: GitHub API commits + triggers `deploy.yml` via `workflow_dispatch`
- `DrWinMacBlogSystem/app.py` — Flask routes, two-tier rate limiting (`verify_passcode` for general; `verify_passcode_expand` tighter for AI calls)
- `blog/metadata.json` — Source of truth for all published posts (slug, title, teaser, sections, image_path)
- `blog/index.html` — Auto-regenerated post listing (do not hand-edit card HTML; it is overwritten on publish)
- `blog/blog_template.html` — Reference template for blog post structure

## Static Site Conventions

- **One shared stylesheet**: `styles.css` at root. All pages link to it with `../styles.css` (from `/blog/`) or `styles.css` (from root). Do not create page-specific CSS files.
- **CSS custom properties** drive all design tokens — colors (`--ember`, `--royal`, `--wine`, `--ink`), spacing (`--sec`, `--sec-tight`), and radius (`--radius`, `--radius-lg`) are all in `:root`.
- **No JavaScript framework** — navigation, menus, and interactivity are handled with minimal vanilla JS inline in each HTML file.
- **Blog post structure** follows a fixed 4-section pattern (see `blog/blog_template.html`): "The Part Most People Aren't Watching" → "What's Actually Changing" → "Why This Actually Matters" → "Where This Quietly Leads".
- Blog post images live in `assets/blog/` and are referenced as `../assets/blog/filename.jpg` from post files.

## Deployment

- **Static site**: Automatic on `git push origin main`. The `deploy.yml` workflow FTPs everything **except** `DrWinMacBlogSystem/`, `Backup/`, `.git*`, `.vscode/`, and dotfiles.
- **API (Render)**: Deployed independently at `https://drwinmac-blog.onrender.com`. Start command: `cd DrWinMacBlogSystem && gunicorn app:app --workers=1 --timeout=120`. Health check: `GET /api/status`.
- `render.yaml` is at the repo root but only defines the Render service — it is **not** used by the FTP deploy.

## Local API Development

```bash
cd DrWinMacBlogSystem
pip install -r requirements.txt
# Create .env with: OPENAI_API_KEY, ADMIN_PASSCODE, SMTP_USER, SMTP_PASSWORD, GITHUB_TOKEN
python app.py  # runs on port 5001
```

Admin UI auto-detects environment: port `5001` → same-origin (Flask served), port `5500` → proxies to `http://127.0.0.1:5001`.

## Required Environment Variables

| Variable                                               | Where set                                                   |
| ------------------------------------------------------ | ----------------------------------------------------------- |
| `OPENAI_API_KEY`                                       | Render dashboard                                            |
| `ADMIN_PASSCODE`                                       | Render dashboard                                            |
| `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_HOST`, `SMTP_PORT` | Render dashboard                                            |
| `GITHUB_TOKEN`                                         | Render dashboard (needs `contents:write` + `actions:write`) |
| `GITHUB_REPO`                                          | `render.yaml` (value: `drwinmac-wq/drwinmac-blog`)          |
| `FTP_HOST`, `FTP_USERNAME`, `FTP_PASSWORD`             | GitHub Actions secrets                                      |

## Key Patterns

- **No database** — `blog/metadata.json` is the only data store. `BlogPublisher` reads/writes it directly and commits it to GitHub on every publish.
- **Auth**: Bearer token in `Authorization` header checked against `ADMIN_PASSCODE`. Passcode stored in `localStorage` in the admin UI.
- **Voice consistency**: `engine.py` contains a `_load_voice_profile()` string that is injected into every GPT-4o prompt. Never alter this profile without reviewing all existing posts for consistency.
- **`Backup/`** is a snapshot of static site files only — it is excluded from FTP deploys and not part of normal workflow.
