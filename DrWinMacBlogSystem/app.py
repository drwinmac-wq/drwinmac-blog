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
import json
import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from functools import wraps
from typing import Dict, Optional

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

RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '10'))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))

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

# ─── ROUTES: ADMIN INTERFACE ─────────────────────────────────────────────

@app.route('/')
def index():
    """Serve login page"""
    return send_from_directory('admin', 'login.html')

@app.route('/admin/')
@app.route('/admin/index.html')
def admin_index():
    """Serve admin dashboard"""
    return send_from_directory('admin', 'blog_admin_2_0.html')

@app.route('/admin/<path:filename>')
def admin_static(filename):
    """Serve admin static files"""
    return send_from_directory('admin', filename)


# Legacy/ported-site compatibility routes
# Some static copies of the site link to the admin folder under
# `/DrWinMacBlogSystem/admin/...`. Add routes that mirror those
# paths so the ported site links resolve without editing the static files.
@app.route('/DrWinMacBlogSystem/admin/')
@app.route('/DrWinMacBlogSystem/admin/index.html')
def legacy_admin_index():
    """Redirect or serve the main admin dashboard for legacy links"""
    return send_from_directory('admin', 'admin-dashboard.html')


@app.route('/DrWinMacBlogSystem/admin/<path:filename>')
def legacy_admin_static(filename):
    """Serve admin static files for legacy paths"""
    return send_from_directory('admin', filename)


@app.route('/favicon.ico')
def favicon():
    """Return empty favicon response (avoid 404 during development)."""
    return ('', 204)

# ─── ROUTES: API ENDPOINTS ───────────────────────────────────────────────

@app.route('/api/status', methods=['GET'])
@verify_passcode
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
@verify_passcode
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
        
        if not short_post:
            return jsonify({'error': 'short_post is required'}), 400

        if mode not in ['smart', 'research', 'voice']:
            return jsonify({'error': 'mode must be smart, research, or voice'}), 400
        logger.info(f"Starting expansion in {mode} mode")
        
        # Run async expansion
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            expanded = loop.run_until_complete(engine.expand_post(short_post, mode))
            
            # Generate preview HTML (publisher may not be initialized in error cases)
            preview_html = publisher.generate_preview_html(expanded) if publisher else ""
            
            # Send email preview
            email_sent = False
            if email_service:
                email_sent = loop.run_until_complete(
                    email_service.send_preview(expanded)
                )
            
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
                'email_sent': email_sent
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
