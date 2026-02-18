# -*- coding: utf-8 -*-
"""
Dr.WinMac AI Blog Expansion Engine
OpenAI GPT-4o powered content expansion in Dr.WinMac voice
"""

import asyncio
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

class DrWinMacExpansionEngine:
    """
    AI-powered blog expansion that:
    1. Parses short posts
    2. Researches context
    3. Expands in Dr.WinMac voice using GPT-4o
    4. Structures for blog template
    """
    
    def __init__(self, openai_api_key: str):
        """Initialize engine with OpenAI API key"""
        self.client = OpenAI(api_key=openai_api_key)
        self.voice_profile = self._load_voice_profile()
        logger.info("DrWinMacExpansionEngine initialized")
    
    def _load_voice_profile(self) -> str:
        """Load Dr.WinMac voice and style guidelines"""
        return """
VOICE & STYLE (CRITICAL - MUST FOLLOW):
-----------------------------------------
* Calm, reflective, observational tone
* Book-style cadence with natural paragraph breaks
* Short to medium paragraphs with breathing room
* Occasional ellipses (...) for thoughtful pauses
* NO hype language, dramatic claims, or corporate speak
* NO generic AI tone—sound like a thoughtful human observer
* Explain complex topics without jargon overload
* Grounded, honest perspective on tech and infrastructure

ARTICLE STRUCTURE (MUST FOLLOW):
-----------------------------------------
1. LEAD (2-3 sentences)
   - Grounded, observational opening
   - Sets context without hype
   
2. "The Part Most People Aren't Watching" (1-2 paragraphs)
   - Overlooked reality, quiet shift happening
   - Establish why this matters despite low visibility
   
3. "What's Actually Changing" (2-3 paragraphs)
   - Deeper technical context
   - No jargon overload
   - Real mechanics of the shift
   
4. "Why This Actually Matters" (2-3 paragraphs)
   - Flexible impact lens
   - Connect to reader concern naturally
   - Honest about both benefits and limitations
   
5. "Where This Quietly Leads" (1-2 paragraphs)
   - Realistic future trajectory
   - NO hype predictions
"""
    
    async def expand_post(self, short_post: str, mode: str = 'smart') -> Dict:
        """
        Expand short post into full article
        
        Args:
            short_post: User's short post text
            mode: 'smart' (balanced), 'research' (heavy sources), 'voice' (minimal research)
        
        Returns:
            Dict with title, slug, lead, sections, teaser, seo, date
        """
        
        logger.info(f"Expanding post in {mode} mode")
        
        # Step 1: Parse the short post
        parsed = self._parse_short_post(short_post)
        logger.info(f"Parsed topic: {parsed['topic']}")
        
        # Step 2: Gather research context (if needed)
        research_data = {}
        if mode in ['smart', 'research']:
            research_data = self._prepare_research_context(parsed['topic'], mode)
            logger.info(f"Research context prepared")
        
        # Step 3: Expand with OpenAI
        expanded = await self._expand_with_gpt4o(parsed, research_data, mode)
        logger.info(f"Expansion complete: {expanded['title']}")
        
        # Step 4: Structure for template
        structured = self._structure_output(expanded, parsed)
        logger.info(f"Ready to publish: {structured['slug']}")
        
        return structured
    
    def _parse_short_post(self, post: str) -> Dict:
        """Extract key information from short post"""
        
        lines = [l.strip() for l in post.strip().split('\n') if l.strip()]
        paragraphs = [p.strip() for p in post.split('\n\n') if p.strip()]
        
        # Extract title (first line, remove special characters)
        title = lines[0] if lines else "Untitled Post"
        title = re.sub(r'[^\w\s\-:&.,?!]', '', title).strip()
        
        # Extract topic for research
        topic = self._extract_topic(title, paragraphs)
        
        # Find lead candidate
        lead_candidate = ""
        if len(paragraphs) > 1:
            for para in paragraphs[1:]:
                if len(para) > 100:
                    lead_candidate = para
                    break
        
        if not lead_candidate and paragraphs:
            lead_candidate = paragraphs[0]
        
        return {
            'title': title,
            'topic': topic,
            'original_post': post,
            'lead_candidate': lead_candidate,
            'paragraphs': paragraphs
        }
    
    def _extract_topic(self, title: str, paragraphs: List[str]) -> str:
        """Extract main topic from title/content"""
        
        title_lower = title.lower()
        
        # Look for topic patterns
        patterns = [
            r'[\w\s]+ data centers?',
            r'ai [\w\s]+ infrastructure',
            r'space-based [\w\s]+',
            r'orbital [\w\s]+',
            r'automation [\w\s]+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title_lower)
            if match:
                return match.group(0)
        
        # Fallback to colon-split
        if ':' in title:
            return title.split(':')[-1].strip()
        
        return title
    
    def _prepare_research_context(self, topic: str, mode: str) -> Dict:
        """
        Prepare research context to weave into expansion
        
        In production, this would integrate real search APIs (Serper, DuckDuckGo, etc.)
        For now, returns template placeholders
        """
        
        context = {
            'topic': topic,
            'research_areas': [
                f'Company developments in {topic}',
                f'Environmental or technical implications of {topic}',
                f'Recent industry news and announcements about {topic}',
                f'Academic or technical research on {topic}',
                f'Market trends and projections for {topic}'
            ]
        }
        
        if mode == 'research':
            context['depth'] = 'heavy'
            context['note'] = 'Focus on multiple sources and detailed statistics'
        else:
            context['depth'] = 'balanced'
            context['note'] = 'Natural weaving of 2-3 key research points'
        
        return context
    
    async def _expand_with_gpt4o(
        self,
        parsed: Dict,
        research: Dict,
        mode: str
    ) -> Dict:
        """Use GPT-4o to expand content in Dr.WinMac voice"""
        
        logger.info("Calling OpenAI GPT-4o...")
        
        # System prompt with voice profile
        system_prompt = f"""You are an AI content writer expanding a short blog post into a full article in the Dr.WinMac voice.

{self.voice_profile}

OUTPUT FORMAT:
Return valid JSON with these exact fields:
{{
    "title": "Refined title",
    "seo_description": "1-2 sentence SEO summary",
    "lead": "Opening paragraph",
    "sections": [
        {{"heading": "The Part Most People Aren't Watching", "body": "1-2 paragraphs"}},
        {{"heading": "What's Actually Changing", "body": "2-3 paragraphs"}},
        {{"heading": "Why This Actually Matters", "body": "2-3 paragraphs"}},
        {{"heading": "Where This Quietly Leads", "body": "1-2 paragraphs"}}
    ],
    "teaser": "One compelling sentence"
}}"""
        
        # User prompt
        user_prompt = f"""ORIGINAL POST:
{parsed['original_post']}

TOPIC: {parsed['topic']}
MODE: {mode}

Expand this into a full blog post. Return only valid JSON."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2500
            )
            
            # The OpenAI client may return the completion as a string
            # containing JSON, or as a JSON-like object depending on the
            # client/version and response_format used. Handle both.
            raw_content = None
            try:
                raw_content = response.choices[0].message.content
            except Exception:
                # Fallback for alternate shapes
                raw_content = getattr(response.choices[0].message, 'content', None) or getattr(response.choices[0], 'text', None)

            if raw_content is None:
                raise ValueError('No content returned from OpenAI')

            if isinstance(raw_content, (dict, list)):
                expanded = raw_content
            else:
                # Try to parse string content as JSON; if that fails,
                # attempt to extract the first JSON object substring.
                if isinstance(raw_content, bytes):
                    raw_content = raw_content.decode('utf-8')

                if isinstance(raw_content, str):
                    try:
                        expanded = json.loads(raw_content)
                    except json.JSONDecodeError:
                        # Attempt to extract JSON object with a simple regex
                        import re as _re

                        m = _re.search(r"\{[\s\S]*\}", raw_content)
                        if m:
                            try:
                                expanded = json.loads(m.group(0))
                            except json.JSONDecodeError as ex:
                                raise ValueError(f"Failed to parse JSON from model output: {ex}\nraw: {raw_content[:300]}")
                        else:
                            raise ValueError(f"Model output not valid JSON: {raw_content[:300]}")
                else:
                    raise ValueError(f"Unexpected content type from model: {type(raw_content)}")

            # Ensure we have a mapping/object
            if not isinstance(expanded, dict):
                raise ValueError(f"Model returned JSON of unexpected type: {type(expanded)}")

            # Validate required fields
            required = ['title', 'seo_description', 'lead', 'sections', 'teaser']
            missing = [f for f in required if f not in expanded]
            if missing:
                raise ValueError(f"Missing fields from model output: {', '.join(missing)}")
            
            logger.info(f"GPT-4o expansion successful")
            return expanded
        
        except Exception as e:
            logger.error(f"OpenAI expansion failed: {e}")
            raise
    
    def _structure_output(self, expanded: Dict, parsed: Dict) -> Dict:
        """Structure expansion output for blog template"""
        
        title = expanded['title']
        slug = self._generate_slug(title)
        
        return {
            'title': title,
            'slug': slug,
            'seo': expanded['seo_description'],
            'lead': expanded['lead'],
            'sections': expanded['sections'],
            'teaser': expanded['teaser'],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'kicker': 'Under the Radar Tech',
            'image_path': f'../assets/blog/{slug}.jpg',
            'image_alt': f'Conceptual illustration: {title.lower()}'
        }
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-safe slug from title"""
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')[:60]
