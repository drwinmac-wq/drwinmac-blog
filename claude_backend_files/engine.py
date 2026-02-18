# -*- coding: utf-8 -*-
"""
Dr.WinMac AI Blog Expansion Engine
GPT-4o powered content expansion in the Dr.WinMac voice.
"""

import json
import re
import logging
from datetime import datetime
from typing import Dict, List

from openai import OpenAI

logger = logging.getLogger(__name__)


VOICE_PROFILE = """
VOICE & STYLE (CRITICAL — MUST FOLLOW):
-----------------------------------------
* Calm, reflective, observational tone
* Book-style cadence with natural paragraph breaks
* Short to medium paragraphs with breathing room
* Occasional ellipses (...) for thoughtful pauses
* NO hype language, dramatic claims, or corporate speak
* NO generic AI tone — sound like a thoughtful human observer
* Explain complex topics without jargon overload
* Grounded, honest perspective on tech and infrastructure

ARTICLE STRUCTURE (MUST FOLLOW):
-----------------------------------------
1. LEAD (2-3 sentences) — grounded, observational opening
2. "The Part Most People Aren't Watching" — overlooked reality, quiet shift
3. "What's Actually Changing" — deeper technical context, no jargon overload
4. "Why This Actually Matters" — impact lens, honest about limits
5. "Where This Quietly Leads" — realistic trajectory, no hype predictions
"""


class DrWinMacExpansionEngine:
    """
    AI-powered blog expansion.
    expand_post() is the only public method app.py calls.
    """

    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        logger.info("DrWinMacExpansionEngine initialized")

    # ── Public API ────────────────────────────────────────────────────────────

    async def expand_post(self, short_post: str, mode: str = 'smart') -> Dict:
        """
        Expand a short post into a full structured article.

        Returns a dict with keys:
            title, slug, seo, lead, sections, teaser, date
        (This is the exact shape /api/expand returns and /api/publish expects.)
        """
        logger.info(f"Expanding post — mode: {mode}")

        parsed   = self._parse_short_post(short_post)
        research = self._prepare_research_context(parsed['topic'], mode) if mode in ('smart', 'research') else {}
        expanded = self._expand_with_gpt4o(parsed, research, mode)
        result   = self._structure_output(expanded, parsed)

        logger.info(f"Expansion complete: {result['title']}")
        return result

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_short_post(self, post: str) -> Dict:
        lines      = [l.strip() for l in post.strip().split('\n') if l.strip()]
        paragraphs = [p.strip() for p in post.split('\n\n') if p.strip()]

        # First non-empty line becomes the working title
        raw_title = lines[0] if lines else "Untitled Post"
        # Strip emojis and most non-standard chars, keep punctuation
        title = re.sub(r'[^\w\s\-:&.,?!]', '', raw_title).strip()

        topic = self._extract_topic(title, paragraphs)

        # Best lead candidate: first paragraph with real substance
        lead_candidate = ''
        for para in (paragraphs[1:] if len(paragraphs) > 1 else paragraphs):
            if len(para) > 80:
                lead_candidate = para
                break
        if not lead_candidate and paragraphs:
            lead_candidate = paragraphs[0]

        return {
            'title':          title,
            'topic':          topic,
            'original_post':  post,
            'lead_candidate': lead_candidate,
            'paragraphs':     paragraphs
        }

    def _extract_topic(self, title: str, paragraphs: List[str]) -> str:
        title_lower = title.lower()
        patterns = [
            r'[\w\s]+ data centers?',
            r'ai [\w\s]+ infrastructure',
            r'space-based [\w\s]+',
            r'orbital [\w\s]+',
            r'automation [\w\s]+',
        ]
        for p in patterns:
            m = re.search(p, title_lower)
            if m:
                return m.group(0)
        if ':' in title:
            return title.split(':')[-1].strip()
        return title

    # ── Research context ──────────────────────────────────────────────────────

    def _prepare_research_context(self, topic: str, mode: str) -> Dict:
        """
        Lightweight research scaffolding passed to GPT-4o prompt.
        In a future iteration this can call a real search API.
        """
        return {
            'topic': topic,
            'depth': 'heavy' if mode == 'research' else 'balanced',
            'areas': [
                f'Company developments in {topic}',
                f'Environmental or technical implications of {topic}',
                f'Recent industry news about {topic}',
                f'Market trends and projections for {topic}'
            ]
        }

    # ── GPT-4o expansion ─────────────────────────────────────────────────────

    def _expand_with_gpt4o(self, parsed: Dict, research: Dict, mode: str) -> Dict:
        """
        Call GPT-4o and return the parsed JSON response.
        The OpenAI client is synchronous; app.py wraps the whole async method
        in asyncio.new_event_loop().run_until_complete(), so this works fine.
        """
        system_prompt = f"""You are an AI content writer expanding a short blog post
into a full article in the Dr.WinMac voice.

{VOICE_PROFILE}

OUTPUT FORMAT — return ONLY valid JSON with exactly these fields:
{{
    "title":           "Refined, non-hype title (no emojis)",
    "seo_description": "1-2 sentence SEO summary",
    "lead":            "Opening paragraph (2-3 sentences, grounded)",
    "sections": [
        {{"heading": "The Part Most People Aren't Watching", "body": "1-2 paragraphs"}},
        {{"heading": "What's Actually Changing",             "body": "2-3 paragraphs"}},
        {{"heading": "Why This Actually Matters",            "body": "2-3 paragraphs"}},
        {{"heading": "Where This Quietly Leads",             "body": "1-2 paragraphs"}}
    ],
    "teaser": "One compelling sentence for the blog index card"
}}

CRITICAL: Match the calm, reflective voice. No hype. No corporate speak. Sound human."""

        depth_note = {
            'research': 'Focus on research integration and multiple angles.',
            'voice':    'Focus on voice and cadence over research depth.',
        }.get(mode, 'Balance depth with readability.')

        user_prompt = f"""ORIGINAL POST:
{parsed['original_post']}

TOPIC: {parsed['topic']}
MODE: {mode} — {depth_note}

RESEARCH CONTEXT:
{json.dumps(research, indent=2)}

Expand this into a full Dr.WinMac blog post. Return only valid JSON."""

        logger.info("Calling OpenAI GPT-4o...")

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=2500
        )

        expanded = json.loads(response.choices[0].message.content)

        # Validate required fields are present
        required = ('title', 'seo_description', 'lead', 'sections', 'teaser')
        missing  = [f for f in required if f not in expanded]
        if missing:
            raise ValueError(f"GPT-4o response missing fields: {', '.join(missing)}")

        logger.info(f"GPT-4o expansion successful — {len(expanded.get('sections', []))} sections")
        return expanded

    # ── Output structuring ────────────────────────────────────────────────────

    def _structure_output(self, expanded: Dict, parsed: Dict) -> Dict:
        """
        Map GPT-4o output to the final shape expected by:
          - /api/expand response
          - /api/publish request body
          - BlogPublisher.generate_html()
        """
        title = expanded['title']
        slug  = self._generate_slug(title)

        return {
            'title':       title,
            'slug':        slug,
            'seo':         expanded['seo_description'],   # note: GPT returns 'seo_description'
            'lead':        expanded['lead'],
            'sections':    expanded['sections'],
            'teaser':      expanded['teaser'],
            'date':        datetime.now().strftime('%Y-%m-%d'),
            'image_path':  f'../assets/blog/{slug}.jpg',
            'image_alt':   f'Illustration: {title.lower()}'
        }

    def _generate_slug(self, title: str) -> str:
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')[:60]
