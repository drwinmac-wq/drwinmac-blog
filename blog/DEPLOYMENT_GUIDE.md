# Dr.WinMac AI Blog System - Deployment Guide

## Overview
This system takes your short GPT posts and expands them into full Dr.WinMac blog posts with:
- Auto-research from multiple sources
- Voice expansion matching your book style
- Email preview workflow with one-click approval
- Auto-generation of HTML files for publishing

## Files Included
1. `drwinmac-blog-admin-v2.html` - Enhanced local admin interface
2. `drwinmac_expansion_engine.py` - AI expansion backend
3. This deployment guide

## Phase 1: Local Admin Tool Setup (5 minutes)

### Quick Start
1. Download `drwinmac-blog-admin-v2.html` 
2. Double-click to open in your browser
3. Paste a short GPT post
4. Click "Expand & Email Preview"

**That's it for the basic version.** The interface will simulate the workflow and show you exactly how it will work.

## Phase 2: Backend Integration (Production)

### Requirements
- Python 3.8+
- Anthropic API key
- Email service (Gmail/SendGrid)
- Optional: Netlify/Vercel for hosting

### Installation

1. **Install Dependencies**
```bash
pip install anthropic requests smtplib email-mime-types
```

2. **Configure Email Service**

For Gmail:
- Enable 2-factor authentication
- Generate an app password
- Use these settings:
  - SMTP Server: smtp.gmail.com
  - Port: 587
  - Username: your-email@gmail.com
  - Password: your-app-password

For SendGrid (recommended for production):
- Sign up at sendgrid.com
- Get API key
- Update email configuration in the Python file

3. **Get Anthropic API Key**
- Sign up at console.anthropic.com
- Generate API key
- Add to environment variables or config

4. **Configure the Backend**

Edit `drwinmac_expansion_engine.py`:
```python
email_config = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'from_email': 'blog@drwinmac.tech',
    'username': 'your-actual-email@gmail.com',
    'password': 'your-actual-app-password'
}

engine = DrWinMacExpansionEngine(
    anthropic_api_key="your-actual-anthropic-key",
    email_config=email_config
)
```

### Testing the Backend

```bash
python drwinmac_expansion_engine.py
```

This will:
1. Parse the example short post
2. Simulate research gathering
3. Expand content using AI
4. Send preview email to jeremy@drwinmac.tech

## Phase 3: Web Search Integration (Enhanced Research)

### Add Real Research Capability

Install additional dependencies:
```bash
pip install duckduckgo-search newspaper3k beautifulsoup4
```

Add this research module to the Python file:

```python
import asyncio
from duckduckgo_search import DDGS
import newspaper
from newspaper import Article

class ResearchEngine:
    def __init__(self):
        self.ddg = DDGS()
    
    async def research_topic(self, topic: str, mode: str = 'smart') -> Dict:
        """Enhanced research using real web search"""
        
        research_data = {
            'companies': [],
            'environmental_data': [],
            'technical_research': [],
            'recent_news': []
        }
        
        # Search queries for different aspects
        queries = {
            'companies': f"{topic} companies development",
            'environmental_data': f"{topic} environmental impact data",
            'technical_research': f"{topic} technical research papers",
            'recent_news': f"{topic} news 2024 2025"
        }
        
        for category, query in queries.items():
            try:
                results = self.ddg.text(query, max_results=5)
                for result in results[:3]:  # Top 3 results per category
                    research_data[category].append({
                        'title': result['title'],
                        'snippet': result['body'],
                        'url': result['href']
                    })
            except Exception as e:
                print(f"Search failed for {category}: {e}")
                
        return research_data
```

## Phase 4: Integration with Admin Interface

### Connect Frontend to Backend

Add this JavaScript to the admin interface:

```javascript
async function callBackendExpansion(shortPost, mode) {
    try {
        const response = await fetch('/api/expand', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                short_post: shortPost,
                mode: mode,
                email: 'jeremy@drwinmac.tech'
            })
        });
        
        const result = await response.json();
        return result;
        
    } catch (error) {
        console.error('Backend expansion failed:', error);
        throw error;
    }
}
```

### Flask/FastAPI Wrapper (Optional)

Create a simple web API wrapper:

```python
from flask import Flask, request, jsonify
from drwinmac_expansion_engine import DrWinMacExpansionEngine

app = Flask(__name__)
engine = DrWinMacExpansionEngine(api_key="your-key", email_config={...})

@app.route('/api/expand', methods=['POST'])
async def expand_post():
    data = request.json
    short_post = data['short_post']
    mode = data.get('mode', 'smart')
    
    # Expand the post
    result = await engine.expand_post(short_post, mode)
    
    # Send email preview
    await engine.send_email_preview(result)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
```

## Phase 5: Email Approval Workflow

### Email Processing

Set up email monitoring for approvals:

```python
import imaplib
import email
from email.mime.text import MIMEText

class EmailProcessor:
    def __init__(self, email_config):
        self.config = email_config
        
    def check_for_approvals(self):
        """Check for approval/edit emails"""
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(self.config['username'], self.config['password'])
            mail.select('inbox')
            
            # Search for approval emails
            status, messages = mail.search(None, 'SUBJECT "APPROVE:"')
            
            for msg_id in messages[0].split():
                # Process approval
                self.process_approval(mail, msg_id)
                
            # Search for edit requests
            status, messages = mail.search(None, 'SUBJECT "EDIT:"')
            
            for msg_id in messages[0].split():
                # Process edits
                self.process_edits(mail, msg_id)
                
        except Exception as e:
            print(f"Email processing failed: {e}")
    
    def process_approval(self, mail, msg_id):
        """Process approval and auto-publish"""
        # Extract slug from subject
        # Generate final HTML files
        # Optionally auto-commit to Git
        pass
        
    def process_edits(self, mail, msg_id):
        """Process edit requests and re-send preview"""
        # Parse edit instructions
        # Apply changes
        # Re-send preview
        pass
```

## Phase 6: Git Auto-Deployment

### Automatic Publishing

Add Git integration:

```python
import subprocess
import os

class GitPublisher:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
    
    def publish_post(self, post_data: Dict):
        """Generate files and push to Git"""
        
        # Generate blog post HTML
        post_html = self.generate_post_html(post_data)
        post_filename = f"blog/{post_data['slug']}.html"
        
        # Generate index card HTML
        card_html = self.generate_card_html(post_data)
        
        # Write post file
        with open(os.path.join(self.repo_path, post_filename), 'w') as f:
            f.write(post_html)
        
        # Update blog index (you'll need to implement index injection)
        self.update_blog_index(card_html)
        
        # Git commit and push
        try:
            subprocess.run(['git', 'add', '.'], cwd=self.repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', f'New post: {post_data["title"]}'], cwd=self.repo_path, check=True)
            subprocess.run(['git', 'push'], cwd=self.repo_path, check=True)
            
            print(f"Published: {post_data['title']}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Git operation failed: {e}")
            return False
```

## Complete Workflow

Once everything is set up:

1. **Write Short Post**: Use ChatGPT to create your short post
2. **Paste & Expand**: Open admin tool, paste post, click expand
3. **Auto-Research**: System researches topic across multiple sources
4. **AI Expansion**: Content expanded in your voice using Anthropic API
5. **Email Preview**: Formatted preview sent to your email
6. **Approve/Edit**: Reply with "Approved" or edit instructions
7. **Auto-Publish**: System generates HTML files and pushes to Git
8. **Live**: Netlify auto-deploys your new post

## Maintenance & Costs

### Ongoing Costs
- Anthropic API: ~$5-20/month (depends on usage)
- Email service: Free (Gmail) or $15/month (SendGrid Pro)
- Hosting: Free (Netlify) or $10/month (upgraded)

### Maintenance Level
- **Week 1-4**: Daily tweaks as you refine the voice matching
- **Month 2+**: Nearly zero maintenance, just write and approve

## Scaling to Clients

This same system can be cloned for clients:
1. Fork the repo per client
2. Adjust voice profile and template
3. Point to client's domain and email
4. Each client gets their own automated blog system

## Troubleshooting

### Common Issues

**Email not sending:**
- Check email credentials
- Verify 2FA and app passwords
- Test SMTP connection manually

**AI expansion too generic:**
- Refine voice profile with more examples
- Add more specific restrictions
- Increase research depth

**Research returning poor results:**
- Refine search queries
- Add more specific topic extraction
- Implement result filtering

**Git push failing:**
- Check SSH keys
- Verify repository permissions
- Test manual git operations

## Next Steps

1. **Start with Phase 1** - Get familiar with the interface
2. **Set up Phase 2** - Get the basic AI expansion working
3. **Add Phase 3** - Enhance research capabilities  
4. **Implement Phase 4** - Connect frontend to backend
5. **Deploy Phase 5** - Email approval workflow
6. **Optimize Phase 6** - Auto-publishing pipeline

Each phase builds on the previous one. You can stop at any phase and still have a working system that saves you significant time.

The end result: paste a short post, get a publication-ready blog post in your voice, delivered to your email for approval. One-click publishing from there.
