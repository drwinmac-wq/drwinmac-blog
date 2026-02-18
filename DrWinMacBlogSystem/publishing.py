"""
Blog Publishing Utilities
Handles HTML generation, file management, GitHub integration, and blog index updates.
"""

import json
import logging
import os
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import requests

logger = logging.getLogger(__name__)


class BlogPublisher:
    """Manage blog post publishing with GitHub persistence."""

    def __init__(self, blog_path: Path):
        self.blog_path = Path(blog_path)
        self.blog_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.blog_path / 'metadata.json'
        self.metadata = self._load_metadata()
        
        # GitHub config
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO', 'drwinmac-wq/drwinmac-blog')
        self.github_api = 'https://api.github.com'
        self.blog_dir = 'blog'  # Directory in repo where blog posts live
        
        logger.info(f"BlogPublisher ready — path: {self.blog_path.resolve()}")
        if self.github_token:
            logger.info(f"GitHub integration enabled — repo: {self.github_repo}")
        else:
            logger.warning("GITHUB_TOKEN not set — blog posts won't persist to GitHub")

    # ── Metadata helpers ─────────────────────────────────────────────────────

    def _load_metadata(self) -> Dict:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not read metadata.json: {e}")
        return {'posts': []}

    def _save_metadata(self):
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save metadata.json: {e}")

    # ── GitHub Integration ───────────────────────────────────────────────────

    def _github_commit(self, filepath: str, content: str, message: str) -> bool:
        """Commit a file to GitHub via API."""
        if not self.github_token:
            logger.warning("GitHub token not configured — skipping GitHub commit")
            return False
        
        try:
            url = f"{self.github_api}/repos/{self.github_repo}/contents/{filepath}"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Get current file SHA if it exists (needed for updates)
            sha = None
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    sha = resp.json()['sha']
            except:
                pass  # File doesn't exist, that's fine
            
            # Encode content as base64
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Prepare commit data
            data = {
                'message': message,
                'content': encoded,
                'branch': 'main'
            }
            if sha:
                data['sha'] = sha
            
            # Commit to GitHub
            resp = requests.put(url, json=data, headers=headers, timeout=10)
            if resp.status_code in [201, 200]:
                logger.info(f"✓ Committed to GitHub: {filepath}")
                return True
            else:
                logger.error(f"GitHub commit failed ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"GitHub commit error: {e}")
            return False

    def _github_commit_binary(self, filepath: str, b64_content: str, message: str) -> bool:
        """Commit a pre-base64-encoded binary file (e.g. image) to GitHub."""
        if not self.github_token:
            logger.warning("GitHub token not configured — skipping binary commit")
            return False
        try:
            url = f"{self.github_api}/repos/{self.github_repo}/contents/{filepath}"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            sha = None
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    sha = resp.json()['sha']
            except:
                pass
            data = {
                'message': message,
                'content': b64_content,
                'branch': 'main'
            }
            if sha:
                data['sha'] = sha
            resp = requests.put(url, json=data, headers=headers, timeout=30)
            if resp.status_code in [200, 201]:
                logger.info(f"✓ Committed binary to GitHub: {filepath}")
                return True
            else:
                logger.error(f"GitHub binary commit failed ({resp.status_code}): {resp.text[:300]}")
                return False
        except Exception as e:
            logger.error(f"GitHub binary commit error: {e}")
            return False

    def _trigger_workflow_dispatch(self) -> bool:
        """Trigger the GitHub Actions deploy workflow via workflow_dispatch event."""
        if not self.github_token:
            return False
        try:
            url = f"{self.github_api}/repos/{self.github_repo}/actions/workflows/deploy.yml/dispatches"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            data = {'ref': 'main'}
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            if resp.status_code == 204:
                logger.info("✓ Triggered GitHub Actions deploy workflow")
                return True
            else:
                logger.warning(f"workflow_dispatch returned {resp.status_code}: {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"workflow_dispatch error: {e}")
            return False

    # ── HTML Generation ──────────────────────────────────────────────────────

    def generate_html(self, post_data: Dict) -> str:
        """Generate a complete, styled blog post HTML file."""

        title      = post_data.get('title', 'Untitled')
        slug       = post_data.get('slug', 'untitled')
        seo        = post_data.get('seo', '')
        lead       = post_data.get('lead', '')
        teaser     = post_data.get('teaser', '')
        sections   = post_data.get('sections', [])
        date_str   = post_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        raw_image  = post_data.get('image_path', '')
        if raw_image and not raw_image.startswith(('/', '../', 'http')):
            image_path = f'../assets/blog/{raw_image}'
        else:
            image_path = raw_image or '../assets/blog/placeholder.jpg'
        image_alt  = post_data.get('image_alt', f'Image for {title}')

        # Format date for display: 2026-02-17 → February 17, 2026
        try:
            display_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
        except ValueError:
            display_date = date_str

        # Build article sections
        sections_html = ''
        for section in sections:
            heading = section.get('heading', '')
            body    = section.get('body', '')
            # Split multi-paragraph bodies into proper <p> tags
            paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
            body_html  = '\n'.join(f'<p>{p}</p>' for p in paragraphs) if paragraphs else f'<p>{body}</p>'
            heading_html = f'<h2 class="post-section-heading">{heading}</h2>\n        ' if heading else ''
            sections_html += f'''
    <section class="section post-section">
        <div class="container">
            {heading_html}{body_html}
        </div>
    </section>
'''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{seo}">
    <meta property="og:title" content="{title} | Dr.WinMac">
    <meta property="og:description" content="{seo}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://drwinmac.tech/blog/{slug}.html">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title} | Dr.WinMac">
    <meta name="twitter:description" content="{seo}">
    <title>{title} | Dr.WinMac</title>
    <link rel="canonical" href="https://drwinmac.tech/blog/{slug}.html">
    <link rel="stylesheet" href="../styles.css">
</head>
<body>

    <!-- Top Nav -->
    <div class="topbar">
      <div class="container">
        <div class="nav">
          <a class="brand" href="/" aria-label="Dr.WinMac Home">
            <span class="brand-dot"></span>
            <span>Dr.WinMac</span>
          </a>
          <button class="nav-toggle" type="button" aria-label="Menu"></button>
        </div>
      </div>
    </div>
    <div id="global-menu" style="display:none;">
      <a href="/">Home</a>
      <a href="/services.html">Services</a>
      <a href="/about.html">About</a>
      <a href="/ai-curriculum.html">AI Curriculum</a>
      <a href="/blog/" class="active">Blog</a>
      <a class="js-book" href="https://tally.so/r/b5Z886" target="_blank" rel="noopener">Book Now</a>
      <a href="/#contact">Contact</a>
    </div>

    <!-- Featured Image -->
    {f'<section class="section post-featured-image" style="padding-bottom:0"><div class="container"><img src="{image_path}" alt="{image_alt}" style="width:100%;border-radius:var(--radius-lg);display:block;max-height:520px;object-fit:cover;"></div></section>' if image_path and 'placeholder' not in image_path else ''}

    <!-- Post Header -->
    <section class="section post-hero">
        <div class="container">
            <div class="breadcrumb">
                <a href="/blog/">Blog</a> &rsaquo; <span>{title}</span>
            </div>
            <h1 class="post-title">{title}</h1>
            <div class="post-meta">
                <span class="post-date">{display_date}</span>
                <span class="post-category">Under the Radar Tech</span>
            </div>
        </div>
    </section>

    <!-- Lead -->
    <section class="section post-lead">
        <div class="container">
            <p class="lead-paragraph">{lead}</p>
        </div>
    </section>

    <!-- Article Body -->
    {sections_html}

    <!-- Closing Teaser -->
    <section class="section post-closing">
        <div class="container">
            <p class="post-teaser-close">{teaser}</p>
        </div>
    </section>

    <!-- CTA -->
    <section class="section post-cta">
        <div class="container">
            <div class="cta-box">
                <h3>Making complex tech shifts clearer</h3>
                <p>Dr.WinMac explores the infrastructure and automation changes
                   that affect everyone, explained without jargon.</p>
                <a href="/blog/" class="btn primary">Back to Blog</a>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <p>&copy; {datetime.now().year} Dr.WinMac. All rights reserved.</p>
        </div>
    </footer>
    <script>
      document.addEventListener("DOMContentLoaded", function () {{
        var btn = document.querySelector(".nav-toggle");
        var menu = document.getElementById("global-menu");
        if (!btn || !menu) return;
        btn.addEventListener("click", function (e) {{
          e.stopPropagation();
          var open = menu.style.display === "flex";
          menu.style.display = open ? "none" : "flex";
          btn.style.transform = open ? "rotate(0deg)" : "rotate(90deg)";
        }});
        document.addEventListener("click", function () {{
          menu.style.display = "none";
          btn.style.transform = "rotate(0deg)";
        }});
      }});
    </script>

</body>
</html>'''

    def generate_preview_html(self, expanded: Dict) -> str:
        """Lightweight preview for the admin dashboard (not a full page)."""
        sections_html = ''
        for i, section in enumerate(expanded.get('sections', []), 1):
            body_preview = section.get('body', '')[:300]
            sections_html += f'''
            <div class="preview-section">
                <h3>Section {i}: {section.get("heading", "")}</h3>
                <p>{body_preview}...</p>
            </div>'''

        return f'''
        <div class="preview-container">
            <h2>{expanded.get("title", "")}</h2>
            <p><em>Slug:</em> {expanded.get("slug", "")}</p>
            <p><em>SEO:</em> {expanded.get("seo", "")}</p>
            <h3>Lead</h3>
            <p>{expanded.get("lead", "")}</p>
            {sections_html}
            <p><strong>Teaser:</strong> {expanded.get("teaser", "")}</p>
        </div>'''

    # ── File I/O ─────────────────────────────────────────────────────────────

    def save_post(self, slug: str, html_content: str) -> str:
        """Write post HTML to disk AND commit to GitHub. Returns the filename."""
        filename = f'{slug}.html'
        filepath = self.blog_path / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Post saved locally: {filepath}")
            
            # Also commit to GitHub for persistence
            github_path = f'{self.blog_dir}/{filename}'
            self._github_commit(github_path, html_content, f'Publish blog post: {slug}')
            
            return filename
        except Exception as e:
            logger.error(f"Failed to save post: {e}")
            raise

    # ── Blog index ─────────────────────────────────────────────────────────--

    def update_blog_index(self, post_data: Dict) -> bool:
        """
        Add post to metadata.json then regenerate /blog/index.html.
        Returns True if both steps succeed.
        """
        try:
            entry = {
                'slug':       post_data.get('slug'),
                'title':      post_data.get('title'),
                'lead':       post_data.get('lead', ''),
                'teaser':     post_data.get('teaser', ''),
                'date':       post_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'seo':        post_data.get('seo', ''),
                'sections':   post_data.get('sections', []),
                'image_path': post_data.get('image_path', ''),
            }

            # Upsert into metadata (replace if slug already exists)
            self.metadata['posts'] = [
                p for p in self.metadata.get('posts', [])
                if p.get('slug') != entry['slug']
            ]
            self.metadata['posts'].insert(0, entry)  # newest first
            self._save_metadata()

            # Regenerate index.html from metadata
            self._regenerate_index()

            logger.info(f"Blog index updated: {entry['slug']}")
            return True

        except Exception as e:
            logger.error(f"Failed to update blog index: {e}")
            return False

    def _regenerate_index(self):
        """
        Rebuild /blog/index.html from metadata.json.
        This is a full replacement — no marker comment needed.
        """
        posts = sorted(
            self.metadata.get('posts', []),
            key=lambda p: p.get('date', ''),
            reverse=True
        )

        cards_html = ''
        for post in posts:
            slug  = post.get('slug', '')
            title = post.get('title', 'Untitled')
            date  = post.get('date', '')
            tease = post.get('teaser', '')
            raw_img = post.get('image_path', '')

            # Build image path
            if raw_img and not raw_img.startswith(('/', '../', 'http')):
                img_src = f'../assets/blog/{raw_img}'
            elif raw_img:
                img_src = raw_img
            else:
                img_src = ''

            # Format date for display
            try:
                display_date = datetime.strptime(date, '%Y-%m-%d').strftime('%B %d, %Y')
            except (ValueError, TypeError):
                display_date = date

            img_html = f'<div class="post-card-img" style="background-image:url({img_src})"></div>' if img_src else '<div class="post-card-img post-card-img--placeholder"></div>'

            cards_html += f'''
    <article class="post-card">
        <a href="/blog/{slug}.html" class="post-card-img-link">
            {img_html}
        </a>
        <div class="post-card-body">
            <h2 class="post-card-title">
                <a href="/blog/{slug}.html">{title}</a>
            </h2>
            <p class="post-card-teaser">{tease}</p>
        </div>
        <div class="post-card-footer">
            <span class="post-card-date">{display_date}</span>
            <a href="/blog/{slug}.html" class="post-card-read">Read more &rarr;</a>
        </div>
    </article>
'''

        if not cards_html:
            cards_html = '<p class="no-posts">No posts published yet.</p>'

        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Dr.WinMac blog — clear explanations of AI, automation, and infrastructure shifts.">
    <meta property="og:title" content="Blog | Dr.WinMac">
    <meta property="og:description" content="Under the Radar Tech — quiet shifts in AI, automation, and infrastructure explained without the hype.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://drwinmac.tech/blog/">
    <title>Blog | Dr.WinMac</title>
    <link rel="canonical" href="https://drwinmac.tech/blog/">
    <link rel="stylesheet" href="../styles.css">
</head>
<body>

    <!-- Top Nav -->
    <div class="topbar">
      <div class="container">
        <div class="nav">
          <a class="brand" href="/" aria-label="Dr.WinMac Home">
            <span class="brand-dot"></span>
            <span>Dr.WinMac</span>
          </a>
          <button class="nav-toggle" type="button" aria-label="Menu"></button>
        </div>
      </div>
    </div>
    <div id="global-menu" style="display:none;">
      <a href="/">Home</a>
      <a href="/services.html">Services</a>
      <a href="/about.html">About</a>
      <a href="/ai-curriculum.html">AI Curriculum</a>
      <a href="/blog/" class="active">Blog</a>
      <a class="js-book" href="https://tally.so/r/b5Z886" target="_blank" rel="noopener">Book Now</a>
      <a href="/#contact">Contact</a>
    </div>

    <!-- Blog Header -->
    <section class="section blog-hero">
        <div class="container">
            <span class="kicker">Under the Radar Tech</span>
            <h1 style="margin-top:16px;">The Blog</h1>
            <p class="lead">
                Quiet shifts in AI, automation, and infrastructure —
                explained without the hype.
            </p>
        </div>
    </section>

    <!-- Post Listing -->
    <section class="section">
        <div class="container">
            <div class="card-grid">
                {cards_html}
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <p>&copy; {datetime.now().year} Dr.WinMac. All rights reserved.</p>
            <p style="margin-top:8px;"><a href="https://drwinmac-blog.onrender.com/admin/" style="font-size:12px;color:rgba(255,255,255,0.55);text-decoration:none;border:1px solid rgba(255,255,255,0.2);padding:4px 10px;border-radius:999px;" target="_blank" rel="noopener">⚙ Admin</a></p>
        </div>
    </footer>
    <script>
      document.addEventListener("DOMContentLoaded", function () {{
        var btn = document.querySelector(".nav-toggle");
        var menu = document.getElementById("global-menu");
        if (!btn || !menu) return;
        btn.addEventListener("click", function (e) {{
          e.stopPropagation();
          var open = menu.style.display === "flex";
          menu.style.display = open ? "none" : "flex";
          btn.style.transform = open ? "rotate(0deg)" : "rotate(90deg)";
        }});
        document.addEventListener("click", function () {{
          menu.style.display = "none";
          btn.style.transform = "rotate(0deg)";
        }});
      }});
    </script>

</body>
</html>'''

        index_path = self.blog_path / 'index.html'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        logger.info(f"blog/index.html regenerated ({len(posts)} posts)")

        # Commit index.html and metadata.json to GitHub
        self._github_commit('blog/index.html', index_html, 'Update blog index')
        metadata_json = json.dumps(self.metadata, indent=2, ensure_ascii=False)
        self._github_commit('blog/metadata.json', metadata_json, 'Update blog metadata')
        # The push event on each commit above will trigger the GitHub Actions FTP deploy

    # ── Post listing ─────────────────────────────────────────────────────────

    def list_posts(self) -> List[Dict]:
        """Return only metadata-backed posts, newest first.

        Intentionally does NOT fall back to scanning the filesystem.
        Any .html file without a metadata entry is an orphan (e.g. a
        partially-deleted post) and must not reappear in the admin list.
        """
        return list(self.metadata.get('posts', []))

    def _github_delete(self, filepath: str, message: str) -> bool:
        """Delete a file from GitHub via API."""
        if not self.github_token:
            logger.warning("GitHub token not configured — skipping GitHub delete")
            return False
        try:
            url = f"{self.github_api}/repos/{self.github_repo}/contents/{filepath}"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            # Must get the current SHA before deleting
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 404:
                logger.info(f"File not found on GitHub (already gone): {filepath}")
                return True
            if resp.status_code != 200:
                logger.warning(f"Could not fetch SHA for delete ({resp.status_code}): {filepath}")
                return False
            sha = resp.json().get('sha')
            if not sha:
                return False
            data = {'message': message, 'sha': sha, 'branch': 'main'}
            del_resp = requests.delete(url, json=data, headers=headers, timeout=10)
            if del_resp.status_code == 200:
                logger.info(f"✓ Deleted from GitHub: {filepath}")
                return True
            else:
                logger.error(f"GitHub delete failed ({del_resp.status_code}): {del_resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"GitHub delete error: {e}")
            return False

    def delete_post(self, slug: str) -> bool:
        """Delete a post: HTML file, image, metadata entry, index — locally and on GitHub."""
        try:
            # ── 1. Grab image filename from metadata BEFORE we remove the entry ──
            post_meta = next(
                (p for p in self.metadata.get('posts', []) if p.get('slug') == slug),
                None
            )
            image_filename = (post_meta or {}).get('image_path', '').strip()
            # Normalise: strip any path prefix, keep only the bare filename
            if image_filename:
                image_filename = Path(image_filename).name

            # ── 2. Delete the post HTML locally ──
            html_path = self.blog_path / f'{slug}.html'
            if html_path.exists():
                html_path.unlink()
                logger.info(f"Deleted local HTML: {html_path}")

            # ── 3. Delete the image locally (assets/blog/<filename>) ──
            if image_filename:
                # blog_path is ../blog; assets/blog is a sibling of blog/
                assets_dir = self.blog_path.parent / 'assets' / 'blog'
                img_path = assets_dir / image_filename
                if img_path.exists():
                    img_path.unlink()
                    logger.info(f"Deleted local image: {img_path}")
                else:
                    logger.info(f"Image not found locally (may already be gone): {img_path}")

            # ── 4. Remove from metadata and regenerate index ──
            self.metadata['posts'] = [
                p for p in self.metadata.get('posts', [])
                if p.get('slug') != slug
            ]
            self._save_metadata()
            self._regenerate_index()  # also commits index.html + metadata.json to GitHub

            # ── 5. Delete post HTML from GitHub ──
            self._github_delete(
                f'{self.blog_dir}/{slug}.html',
                f'Delete blog post: {slug}'
            )

            # ── 6. Delete image from GitHub ──
            if image_filename:
                self._github_delete(
                    f'assets/blog/{image_filename}',
                    f'Delete image for post: {slug}'
                )

            logger.info(f"Post fully deleted: {slug}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete post: {e}")
            return False
