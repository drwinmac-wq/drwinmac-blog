#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dr.WinMac Blog Automation API
Single entrypoint. Run this file only. Do NOT run blog_api.py.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from engine import DrWinMacExpansionEngine
from publishing import BlogPublisher
from email_helper import EmailService

# ─── SETUP ───────────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='admin', static_url_path='')
app.config['JSON_SORT_KEYS'] = False

# CORS — '*' in dev; set CORS_ORIGINS env var to lock down in production
env_origins = os.getenv('CORS_ORIGINS', '*')
cors_origins = '*' if env_origins == '*' else [o.strip() for o in env_origins.split(',') if o.strip()]

CORS(app, resources={
    r"/api/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ─── CONFIGURATION ───────────────────────────────────────────────────────────

ADMIN_PASSCODE = os.getenv('ADMIN_PASSCODE')
if not ADMIN_PASSCODE:
    raise ValueError("ADMIN_PASSCODE environment variable is required")

RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '10'))
RATE_LIMIT_WINDOW   = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))

# Blog HTML files land here. Adjust BLOG_PATH in .env if needed.
BLOG_PATH = Path(os.getenv('BLOG_PATH', 'blog'))
BLOG_PATH.mkdir(parents=True, exist_ok=True)

# ─── SERVICE INITIALIZATION ───────────────────────────────────────────────────

try:
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    email_config = {
        'smtp_host':  os.getenv('SMTP_HOST', 'mail.privateemail.com'),
        'smtp_port':  int(os.getenv('SMTP_PORT', '587')),
        'from_email': os.getenv('SMTP_USER', ''),
        'username':   os.getenv('SMTP_USER', ''),
        'password':   os.getenv('SMTP_PASSWORD', '')
    }

    engine        = DrWinMacExpansionEngine(openai_key)
    email_service = EmailService(email_config)
    publisher     = BlogPublisher(BLOG_PATH)

    logger.info("All services initialized successfully")

except Exception as e:
    logger.error(f"Initialization failed: {e}")
    engine = email_service = publisher = None

# ─── AUTH & RATE LIMITING ─────────────────────────────────────────────────────

rate_limit_store = defaultdict(list)

def verify_passcode(f):
    """Verify Bearer token and enforce per-IP rate limiting."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        client_ip = request.remote_addr
        now = datetime.now()

        # Slide the window
        rate_limit_store[client_ip] = [
            t for t in rate_limit_store[client_ip]
            if now - t < timedelta(seconds=RATE_LIMIT_WINDOW)
        ]

        if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit exceeded: {client_ip}")
            return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429

        auth = request.headers.get('Authorization', '').strip()
        passcode = auth[7:] if auth.startswith('Bearer ') else auth

        if not passcode or passcode != ADMIN_PASSCODE:
            rate_limit_store[client_ip].append(now)
            logger.warning(f"Invalid passcode from {client_ip}")
            return jsonify({'error': 'Unauthorized. Invalid passcode.'}), 401

        rate_limit_store[client_ip].append(now)
        return f(*args, **kwargs)

    return wrapper

# ─── STATIC / ADMIN ROUTES ───────────────────────────────────────────────────

@app.route('/')
def root():
    return app.send_static_file('login.html')

@app.route('/admin/')
@app.route('/admin/index.html')
def admin_index():
    return app.send_static_file('admin-dashboard.html')

@app.route('/admin/<path:filename>')
def admin_static(filename):
    return send_from_directory('admin', filename)

@app.route('/favicon.ico')
def favicon():
    return ('', 204)

# ─── API: STATUS ─────────────────────────────────────────────────────────────

@app.route('/api/status', methods=['GET'])
@verify_passcode
def api_status():
    return jsonify({
        'status':          'ok',
        'engine_ready':    engine is not None,
        'email_ready':     email_service is not None,
        'publisher_ready': publisher is not None,
        'timestamp':       datetime.now().isoformat()
    })

# ─── API: EXPAND ─────────────────────────────────────────────────────────────

@app.route('/api/expand', methods=['POST'])
@verify_passcode
def api_expand():
    """
    Expand a short post into a full article.

    Request body:
        { "short_post": "...", "mode": "smart" | "research" | "voice" }

    Response — flat fields (dashboard reads these directly, /api/publish sends them back):
        { "success": true, "title", "slug", "seo", "lead",
          "sections", "teaser", "date", "email_sent" }
    """
    if not engine:
        return jsonify({'error': 'AI engine not available'}), 503

    data       = request.json or {}
    short_post = (data.get('short_post') or '').strip()
    mode       = data.get('mode', 'smart')

    if not short_post:
        return jsonify({'error': 'short_post is required'}), 400
    if mode not in ('smart', 'research', 'voice'):
        return jsonify({'error': 'mode must be smart, research, or voice'}), 400

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            expanded = loop.run_until_complete(engine.expand_post(short_post, mode))
        finally:
            loop.close()

        # Email preview is non-fatal — log failures and move on
        email_sent = False
        if email_service:
            try:
                email_sent = email_service.send_preview_sync(expanded)
            except Exception as em:
                logger.warning(f"Email preview skipped: {em}")

        logger.info(f"Expansion OK: {expanded['title']}")

        return jsonify({
            'success':    True,
            'title':      expanded['title'],
            'slug':       expanded['slug'],
            'seo':        expanded['seo'],
            'lead':       expanded['lead'],
            'sections':   expanded['sections'],
            'teaser':     expanded['teaser'],
            'date':       expanded['date'],
            'email_sent': email_sent
        })

    except Exception as e:
        logger.error(f"Expansion failed: {e}", exc_info=True)
        return jsonify({'error': str(e), 'message': 'Content expansion failed.'}), 500

# ─── API: PUBLISH ─────────────────────────────────────────────────────────────

@app.route('/api/publish', methods=['POST'])
@verify_passcode
def api_publish():
    """
    Publish expanded post to /blog/.

    Request body — flat fields (same shape as /api/expand response):
        { "title", "slug", "lead", "sections", "teaser", "seo", "date" }

    Response:
        { "success": true, "filename": "slug.html",
          "index_updated": true, "live_url": "/blog/slug.html" }
    """
    if not publisher:
        return jsonify({'error': 'Publisher not available'}), 503

    data    = request.json or {}
    missing = [f for f in ('title', 'slug', 'lead', 'sections', 'teaser', 'seo') if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    try:
        html          = publisher.generate_html(data)
        filename      = publisher.save_post(data['slug'], html)
        index_updated = publisher.update_blog_index(data)

        logger.info(f"Post published: {filename}")

        return jsonify({
            'success':       True,
            'filename':      filename,
            'index_updated': index_updated,
            'live_url':      f'/blog/{data["slug"]}.html'
        })

    except Exception as e:
        logger.error(f"Publishing failed: {e}", exc_info=True)
        return jsonify({'error': str(e), 'message': 'Publishing failed.'}), 500

# ─── API: POSTS LIST ─────────────────────────────────────────────────────────

@app.route('/api/posts', methods=['GET'])
@verify_passcode
def api_posts():
    if not publisher:
        return jsonify({'error': 'Publisher not available'}), 503
    try:
        posts = publisher.list_posts()
        return jsonify({'success': True, 'posts': posts, 'total': len(posts)})
    except Exception as e:
        logger.error(f"Failed to list posts: {e}")
        return jsonify({'error': str(e)}), 500

# ─── ERROR HANDLERS ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# ─── STARTUP ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port  = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    logger.info(f"Starting Dr.WinMac Blog API on port {port} | blog path: {BLOG_PATH.resolve()}")
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=debug)
