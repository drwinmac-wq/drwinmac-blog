#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dr.WinMac Blog Automation API
Production-ready Flask backend for AI-powered blog publishing

Features:
- GPT-4o content expansion with voice matching
- Email preview delivery
- Automatic HTML generation and blog index updates
- Rate limiting and authentication
- Comprehensive logging and error handling
"""

import os
import re
import json
import base64
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

# ─── SETUP ───────────────────────────────────────────────────────────────

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='admin', static_url_path='')
app.config['JSON_SORT_KEYS'] = False

# Configure CORS
env_origins = os.getenv('CORS_ORIGINS', '*')
origins = [o for o in env_origins.split(',') if o]

# Add common local development origins if not explicitly set
local_variants = ['http://127.0.0.1:5500', 'http://127.0.0.1', 'http://localhost:5500']
for v in local_variants:
    if v not in origins and env_origins != '*':
        origins.append(v)

CORS(app, resources={
    r"/api/*": {
        "origins": origins if origins else '*',
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ─── CONFIGURATION ───────────────────────────────────────────────────────

ADMIN_PASSCODE = os.getenv('ADMIN_PASSCODE')
if not ADMIN_PASSCODE:
    raise ValueError("ADMIN_PASSCODE environment variable required")

RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '200'))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))
# Separate tighter limit for expensive AI calls (expand)
RATE_LIMIT_EXPAND = int(os.getenv('RATE_LIMIT_EXPAND', '20'))

BLOG_PATH = Path(os.getenv('BLOG_PATH', '../blog'))
BLOG_PATH.mkdir(parents=True, exist_ok=True)

# ─── INITIALIZATION ──────────────────────────────────────────────────────

try:
    # Initialize services
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable required")
    
    # Email configuration
    email_config = {
        'smtp_host': os.getenv('SMTP_HOST', 'mail.privateemail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'from_email': os.getenv('SMTP_USER', ''),
        'username': os.getenv('SMTP_USER', ''),
        'password': os.getenv('SMTP_PASSWORD', '')
    }
    
    # Initialize services
    engine = DrWinMacExpansionEngine(openai_key)
    email_service = EmailService(email_config)
    publisher = BlogPublisher(BLOG_PATH)
    
    logger.info("All services initialized successfully")
    
except Exception as e:
    logger.error(f"Initialization failed: {e}")
    engine = None
    email_service = None
    publisher = None

# ─── AUTHENTICATION ──────────────────────────────────────────────────────

rate_limit_store = defaultdict(list)
rate_limit_expand_store = defaultdict(list)

def verify_passcode(f):
    """Decorator to verify admin passcode and enforce rate limiting"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        client_ip = request.remote_addr
        now = datetime.now()
        
        # Clean old requests from rate limit store
        rate_limit_store[client_ip] = [
            t for t in rate_limit_store[client_ip]
            if now - t < timedelta(seconds=RATE_LIMIT_WINDOW)
        ]
        
        # Check rate limit
        if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429
        
        # Get passcode from Authorization header
        auth_header = request.headers.get('Authorization', '').strip()
        passcode = auth_header[7:] if auth_header.startswith('Bearer ') else auth_header
        
        # Verify passcode
        if not passcode or passcode != ADMIN_PASSCODE:
            rate_limit_store[client_ip].append(now)
            logger.warning(f"Invalid passcode attempt from {client_ip}")
            return jsonify({'error': 'Unauthorized. Invalid passcode.'}), 401
        
        # Record successful request
        rate_limit_store[client_ip].append(now)
        
        return f(*args, **kwargs)
    
    return wrapper

def verify_passcode_expand(f):
    """Stricter rate-limit decorator for expensive AI expand calls"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        client_ip = request.remote_addr
        now = datetime.now()
        
        # Auth check (reuse general store for auth failures)
        auth_header = request.headers.get('Authorization', '').strip()
        passcode = auth_header[7:] if auth_header.startswith('Bearer ') else auth_header
        if not passcode or passcode != ADMIN_PASSCODE:
            rate_limit_store[client_ip].append(now)
            logger.warning(f"Invalid passcode attempt from {client_ip}")
            return jsonify({'error': 'Unauthorized. Invalid passcode.'}), 401
        
        # Tight rate limit for expand
        rate_limit_expand_store[client_ip] = [
            t for t in rate_limit_expand_store[client_ip]
            if now - t < timedelta(seconds=RATE_LIMIT_WINDOW)
        ]
        if len(rate_limit_expand_store[client_ip]) >= RATE_LIMIT_EXPAND:
            logger.warning(f"Expand rate limit exceeded for {client_ip}")
            return jsonify({'error': f'Expand rate limit reached ({RATE_LIMIT_EXPAND}/hr). Try again later.'}), 429
        
        rate_limit_expand_store[client_ip].append(now)
        return f(*args, **kwargs)
    
    return wrapper

# ─── ROUTES: ADMIN INTERFACE ─────────────────────────────────────────────

@app.route('/')
@app.route('/admin/')
@app.route('/admin/index.html')
def admin_index():
    """Serve the admin panel"""
    return send_from_directory('admin', 'blog_admin_2_0.html')

@app.route('/admin/<path:filename>')
def admin_static(filename):
    """Serve admin static files"""
    return send_from_directory('admin', filename)


@app.route('/favicon.ico')
def favicon():
    """Return empty favicon response (avoid 404 during development)."""
    return ('', 204)

# ─── ROUTES: API ENDPOINTS ───────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
IMAGE_UPLOAD_DIR = Path(os.getenv('IMAGE_UPLOAD_DIR', '../assets/blog'))

@app.route('/api/upload-image', methods=['POST'])
@verify_passcode
def api_upload_image():
    """Upload a blog post image, auto-renamed for SEO."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400

    # Extension check (case-insensitive)
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        return jsonify({'error': f'File type .{ext} not allowed. Use: {allowed}'}), 400

    # SEO-friendly rename: use provided title slug or fall back to original stem
    title_hint = (request.form.get('title') or '').strip()
    if title_hint:
        slug = re.sub(r'[^a-z0-9]+', '-', title_hint.lower()).strip('-')[:80]
    else:
        stem = f.filename.rsplit('.', 1)[0]
        slug = re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-')[:80]

    safe_name = f'{slug}.{ext}'

    upload_dir = IMAGE_UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Avoid overwriting: append -2, -3 ... if file already exists
    dest = upload_dir / safe_name
    counter = 2
    while dest.exists():
        safe_name = f'{slug}-{counter}.{ext}'
        dest = upload_dir / safe_name
        counter += 1

    f.save(dest)
    logger.info(f'✅ Image uploaded: {dest}')

    # Commit image to GitHub so it persists and triggers FTP deploy
    if publisher:
        with open(dest, 'rb') as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode('utf-8')
        github_path = f'assets/blog/{safe_name}'
        publisher._github_commit_binary(github_path, img_b64, f'Upload blog image: {safe_name}')

    return jsonify({'success': True, 'filename': safe_name})


@app.route('/api/status', methods=['GET'])
def api_status():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'engine_ready': engine is not None,
        'email_ready': email_service is not None,
        'publisher_ready': publisher is not None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/expand', methods=['POST'])
@verify_passcode_expand
def api_expand():
    """
    Expand short post into full article
    
    Request:
    {
        "short_post": "Your short post text...",
        "mode": "smart"  // or "research" or "voice"
    }
    
    Response:
    {
        "success": true,
        "title": "...",
        "slug": "...",
        "lead": "...",
        "sections": [...],
        "preview_html": "...",
        "email_sent": true/false
    }
    """
    
    if not engine:
        logger.error("Engine not initialized")
        return jsonify({'error': 'AI engine not available'}), 503
    
    try:
        # Validate request
        data = request.json or {}
        short_post = (data.get('short_post') or '').strip()
        mode = data.get('mode', 'smart')
        model = data.get('model', 'gpt-4o')

        if not short_post:
            return jsonify({'error': 'short_post is required'}), 400

        if mode not in ['smart', 'research', 'voice']:
            return jsonify({'error': 'mode must be smart, research, or voice'}), 400

        allowed_models = {'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'}
        if model not in allowed_models:
            model = 'gpt-4o'
        logger.info(f"Starting expansion in {mode} mode with model {model}")
        
        # Run async expansion
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            expanded = loop.run_until_complete(engine.expand_post(short_post, mode, model))
            
            # Generate preview HTML (publisher may not be initialized in error cases)
            preview_html = publisher.generate_preview_html(expanded) if publisher else ""
            
            logger.info(f"✅ Expansion successful: {expanded['title']}")
            
            return jsonify({
                'success': True,
                'title': expanded['title'],
                'slug': expanded['slug'],
                'seo': expanded['seo'],
                'lead': expanded['lead'],
                'sections': expanded['sections'],
                'teaser': expanded['teaser'],
                'date': expanded['date'],
                'preview_html': preview_html,
                'email_sent': False
            })
        
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Expansion failed: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Content expansion failed. Check logs for details.'
        }), 500

@app.route('/api/publish', methods=['POST'])
@verify_passcode
def api_publish():
    """
    Publish expanded post to blog
    
    Request:
    {
        "title": "...",
        "slug": "...",
        "lead": "...",
        "sections": [...],
        "teaser": "...",
        "seo": "...",
        "date": "2026-02-17"
    }
    
    Response:
    {
        "success": true,
        "filename": "post-slug.html",
        "index_updated": true,
        "live_url": "/blog/post-slug.html"
    }
    """
    
    if not publisher:
        return jsonify({'error': 'Publisher not available'}), 503
    
    try:
        data = request.json or {}
        
        # Validate required fields
        required = ['title', 'slug', 'lead', 'sections', 'teaser', 'seo']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        logger.info(f"Publishing post: {data['slug']}")
        
        # Generate and save HTML
        html_content = publisher.generate_html(data)
        filename = publisher.save_post(data['slug'], html_content)
        
        # Update blog index
        index_updated = publisher.update_blog_index(data)
        
        logger.info(f"✅ Post published: {filename}")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'index_updated': index_updated,
            'live_url': f'/blog/{data["slug"]}.html'
        })
    
    except Exception as e:
        logger.error(f"Publishing failed: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Publishing failed. Check logs for details.'
        }), 500

@app.route('/api/preview', methods=['POST'])
@verify_passcode
def api_preview():
    """
    Generate HTML preview of expanded content (without publishing)
    
    Request: Same as /api/publish
    Response: { "html": "<html>..." }
    """
    
    if not publisher:
        return jsonify({'error': 'Publisher not available'}), 503
    
    try:
        data = request.json or {}
        html = publisher.generate_html(data)
        
        return jsonify({
            'success': True,
            'html': html
        })
    
    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts', methods=['GET'])
@verify_passcode
def api_posts():
    """
    List published posts with metadata
    
    Response:
    {
        "posts": [
            {
                "slug": "post-slug",
                "title": "Post Title",
                "date": "2026-02-17",
                "teaser": "..."
            }
        ]
    }
    """
    
    if not publisher:
        return jsonify({'error': 'Publisher not available'}), 503
    
    try:
        posts = publisher.list_posts()
        return jsonify({
            'success': True,
            'posts': posts,
            'total': len(posts)
        })
    
    except Exception as e:
        logger.error(f"Failed to list posts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts/<slug>', methods=['DELETE'])
@verify_passcode
def api_delete_post(slug):
    """
    Delete a published post by slug
    """
    if not publisher:
        return jsonify({'error': 'Publisher not available'}), 503
    
    try:
        publisher.delete_post(slug)
        return jsonify({
            'success': True,
            'message': f'Post {slug} deleted'
        })
    
    except Exception as e:
        logger.error(f"Failed to delete post: {e}")
        return jsonify({'error': str(e)}), 500

# ─── ERROR HANDLERS ───────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# ─── STARTUP ──────────────────────────────────────────────────────────────

@app.before_request
def log_request():
    """Log incoming requests"""
    if not request.path.startswith('/admin'):
        logger.debug(f"{request.method} {request.path}")

if __name__ == '__main__':
    if engine and email_service and publisher:
        port = int(os.getenv('PORT', 5001))
        debug = os.getenv('FLASK_ENV', 'production') == 'development'
        
        logger.info(f"🚀 Starting Dr.WinMac Blog API on port {port}")
        logger.info(f"📝 Blog path: {BLOG_PATH}")
        logger.info(f"🔐 Admin passcode configured")
        
        app.run(
            host='127.0.0.1',
            port=port,
            debug=debug,
            use_reloader=debug
        )
    else:
        logger.error("❌ Failed to initialize services. Exiting.")
        exit(1)
