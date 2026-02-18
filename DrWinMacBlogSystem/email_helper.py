"""
Email Service
Sends formatted HTML preview emails via SMTP.
"""

import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict

logger = logging.getLogger(__name__)


class EmailService:
    """Handle SMTP email sending for blog previews."""

    def __init__(self, config: Dict):
        """
        Config keys (all come from .env via app.py):
            smtp_host, smtp_port, from_email, username, password
        """
        self.config     = config
        self.from_email = config.get('from_email', '')
        self.to_email   = 'jeremy@drwinmac.tech'
        logger.info(f"EmailService ready — from: {self.from_email}")

    # ── Public API ────────────────────────────────────────────────────────────

    def send_preview_sync(self, expanded_content: Dict) -> bool:
        """
        Send a formatted blog preview email synchronously.
        Called directly from app.py. Returns True on success, False on failure.
        """
        try:
            html = self._generate_preview_email(expanded_content)

            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Blog Preview: {expanded_content.get('title', 'Untitled')}"
            msg['From']    = self.from_email
            msg['To']      = self.to_email
            msg.attach(MIMEText(html, 'html'))

            self._send_smtp(msg)
            logger.info(f"Preview email sent to {self.to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send preview email: {e}")
            return False

    async def send_preview(self, expanded_content: Dict) -> bool:
        """
        Async wrapper for sending preview emails so callers can await it.
        Runs the blocking SMTP send in a thread executor to avoid blocking
        the event loop.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send_preview_sync, expanded_content)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _send_smtp(self, msg: MIMEMultipart):
        """Blocking SMTP send. Port 465 = SSL, 587 = STARTTLS."""
        port    = self.config.get('smtp_port', 587)
        use_ssl = (port == 465)

        if use_ssl:
            server = smtplib.SMTP_SSL(self.config['smtp_host'], port, timeout=15)
        else:
            server = smtplib.SMTP(self.config['smtp_host'], port, timeout=15)
            server.starttls()

        try:
            server.login(self.config['username'], self.config['password'])
            server.send_message(msg)
        finally:
            server.quit()

    def _generate_preview_email(self, content: Dict) -> str:
        """Build the full HTML email body for a blog preview."""

        title    = content.get('title', 'Untitled')
        slug     = content.get('slug', 'untitled')
        seo      = content.get('seo', '')
        lead     = content.get('lead', '')
        teaser   = content.get('teaser', '')
        date_str = content.get('date', datetime.now().strftime('%Y-%m-%d'))
        sections = content.get('sections', [])

        sections_html = ''
        for i, section in enumerate(sections, 1):
            heading      = section.get('heading', f'Section {i}')
            body         = section.get('body', '')
            body_preview = body[:250] + '...' if len(body) > 250 else body
            sections_html += f'''
            <div style="margin-bottom:24px;padding:16px;background:#f8f9fa;
                        border-radius:8px;border-left:4px solid #2563eb;">
                <h3 style="margin:0 0 8px;color:#1e40af;font-size:16px;">
                    Section {i}: {heading}
                </h3>
                <p style="margin:0;color:#4b5563;line-height:1.6;font-size:14px;">
                    {body_preview}
                </p>
            </div>'''

        approve_url = (
            f"mailto:{self.from_email}?subject=APPROVE: {slug}"
            f"&body=Approved for publishing on {date_str}"
        )
        edit_url = (
            f"mailto:{self.from_email}?subject=EDIT: {slug}"
            f"&body=SECTION 1: {{your revised text here}}"
        )

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         line-height:1.6;color:#2d3748;margin:0;padding:20px;background:#f7fafc;}}
  .wrap {{max-width:600px;margin:0 auto;background:#fff;border-radius:12px;
          overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.1);}}
  .hdr  {{background:linear-gradient(135deg,#2563eb,#1e40af);color:#fff;
          padding:32px 24px;text-align:center;}}
  .hdr h1{{margin:0;font-size:22px;font-weight:700;}}
  .hdr p {{margin:8px 0 0;font-size:15px;opacity:.95;}}
  .body {{padding:32px 24px;}}
  .meta {{background:#f3f4f6;padding:16px;border-radius:8px;margin-bottom:24px;font-size:13px;}}
  .meta p{{margin:4px 0;}}
  .lead {{background:#f3f4f6;padding:16px;border-radius:8px;
          border-left:4px solid #2563eb;font-style:italic;margin-bottom:24px;}}
  .btn  {{display:inline-block;padding:12px 24px;text-decoration:none;
          border-radius:8px;font-weight:600;font-size:14px;margin:4px;}}
  .btn-ok  {{background:#10b981;color:#fff;}}
  .btn-ed  {{background:#f59e0b;color:#fff;}}
  .actions {{text-align:center;margin-bottom:28px;}}
  .ftr  {{background:#f9fafb;padding:20px 24px;border-top:1px solid #e5e7eb;
          font-size:12px;color:#6b7280;text-align:center;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>Blog Preview Ready</h1>
    <p>{title}</p>
  </div>
  <div class="body">
    <div class="actions">
      <a href="{approve_url}" class="btn btn-ok">&#10003; Approve &amp; Publish</a>
      <a href="{edit_url}"    class="btn btn-ed">&#9998; Request Edits</a>
    </div>
    <div class="meta">
      <p><strong>File:</strong> {slug}.html</p>
      <p><strong>Date:</strong> {date_str}</p>
      <p><strong>SEO:</strong> {seo}</p>
      <p><strong>Teaser:</strong> {teaser}</p>
    </div>
    <h3 style="font-size:15px;color:#1f2937;border-bottom:2px solid #e5e7eb;
               padding-bottom:10px;">Opening</h3>
    <div class="lead">{lead}</div>
    <h3 style="font-size:15px;color:#1f2937;border-bottom:2px solid #e5e7eb;
               padding-bottom:10px;">Sections</h3>
    {sections_html}
    <div style="margin-top:28px;padding:16px;background:#eef2ff;border-radius:8px;">
      <strong>How to respond:</strong><br>
      Reply <code>APPROVE</code> to publish as-is, or
      <code>SECTION 2: your revised text</code> to request an edit.
    </div>
  </div>
  <div class="ftr">
    Dr.WinMac AI Blog System &mdash; OpenAI GPT-4o<br>
    Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
  </div>
</div>
</body>
</html>'''
