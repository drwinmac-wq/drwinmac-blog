"""
Blog Publishing Utilities
Handles HTML generation, file management, and blog index updates.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class BlogPublisher:
    """Manage blog post publishing and index page regeneration."""

    def __init__(self, blog_path: Path):
        self.blog_path     = Path(blog_path)
        self.blog_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.blog_path / 'metadata.json'
        self.metadata      = self._load_metadata()
        logger.info(f"BlogPublisher ready — path: {self.blog_path.resolve()}")

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
        image_path = post_data.get('image_path', '../assets/blog/placeholder.jpg')
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
            sections_html += f'''
    <section class="section post-section">
        <div class="container">
            <h2>{heading}</h2>
            {body_html}
        </div>
    </section>
'''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{seo}">
    <title>{title} | Dr.WinMac</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>

    <!-- Navigation -->
    <nav class="nav">
        <div class="container nav-inner">
            <a href="/" class="nav-logo">Dr.WinMac</a>
            <div class="nav-links">
                <a href="/blog/">Blog</a>
                <a href="/about.html">About</a>
                <a href="/services.html">Services</a>
            </div>
        </div>
    </nav>

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

    <!-- CTA -->
    <section class="section post-cta">
        <div class="container">
            <div class="cta-box">
                <h3>Making complex tech shifts clearer</h3>
                <p>Dr.WinMac explores the infrastructure and automation changes
                   that affect everyone, explained without jargon.</p>
                <a href="/blog/" class="btn btn-primary">Back to Blog</a>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <p>&copy; {datetime.now().year} Dr.WinMac. All rights reserved.</p>
        </div>
    </footer>

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
        """Write post HTML to disk. Returns the filename."""
        filename = f'{slug}.html'
        filepath = self.blog_path / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Post saved: {filepath}")
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
                'slug':   post_data.get('slug'),
                'title':  post_data.get('title'),
                'teaser': post_data.get('teaser'),
                'date':   post_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'seo':    post_data.get('seo')
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
        posts = self.metadata.get('posts', [])

        cards_html = ''
        for post in posts:
            slug  = post.get('slug', '')
            title = post.get('title', 'Untitled')
            date  = post.get('date', '')
            tease = post.get('teaser', '')

            # Format date for display
            try:
                display_date = datetime.strptime(date, '%Y-%m-%d').strftime('%B %d, %Y')
            except (ValueError, TypeError):
                display_date = date

            cards_html += f'''
    <article class="card solid">
        <div class="card-meta">
            <span class="card-date">{display_date}</span>
            <span class="card-tag">Under the Radar Tech</span>
        </div>
        <h2 class="card-title">
            <a href="/blog/{slug}.html">{title}</a>
        </h2>
        <p class="card-teaser">{tease}</p>
        <a href="/blog/{slug}.html" class="card-link">Read more &rarr;</a>
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
    <title>Blog | Dr.WinMac</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>

    <!-- Navigation -->
    <nav class="nav">
        <div class="container nav-inner">
            <a href="/" class="nav-logo">Dr.WinMac</a>
            <div class="nav-links">
                <a href="/blog/">Blog</a>
                <a href="/about.html">About</a>
                <a href="/services.html">Services</a>
            </div>
        </div>
    </nav>

    <!-- Blog Header -->
    <section class="section blog-hero">
        <div class="container">
            <h1>Under the Radar Tech</h1>
            <p class="blog-subtitle">
                Quiet shifts in AI, automation, and infrastructure —
                explained without the hype.
            </p>
        </div>
    </section>

    <!-- Post Listing -->
    <section class="section blog-listing">
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
        </div>
    </footer>

</body>
</html>'''

        index_path = self.blog_path / 'index.html'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        logger.info(f"blog/index.html regenerated ({len(posts)} posts)")

    # ── Post listing ─────────────────────────────────────────────────────────

    def list_posts(self) -> List[Dict]:
        """Return list of all known posts, newest first."""
        posts = []
        try:
            for html_file in sorted(self.blog_path.glob('*.html'), reverse=True):
                if html_file.name == 'index.html':
                    continue
                slug = html_file.stem
                # Prefer metadata entry, fall back to filename
                meta = next(
                    (p for p in self.metadata.get('posts', []) if p.get('slug') == slug),
                    None
                )
                if meta:
                    posts.append(meta)
                else:
                    posts.append({
                        'slug':  slug,
                        'title': slug.replace('-', ' ').title(),
                        'date':  datetime.fromtimestamp(
                            html_file.stat().st_mtime
                        ).strftime('%Y-%m-%d')
                    })
        except Exception as e:
            logger.error(f"Failed to list posts: {e}")
        return posts

    def delete_post(self, slug: str) -> bool:
        """Delete a post file and remove it from the index."""
        try:
            filepath = self.blog_path / f'{slug}.html'
            if filepath.exists():
                filepath.unlink()
                self.metadata['posts'] = [
                    p for p in self.metadata.get('posts', [])
                    if p.get('slug') != slug
                ]
                self._save_metadata()
                self._regenerate_index()
                logger.info(f"Post deleted: {slug}")
                return True
            logger.warning(f"Post not found for deletion: {slug}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete post: {e}")
            return False
