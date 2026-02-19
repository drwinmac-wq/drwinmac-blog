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
    
    async def expand_post(
        self,
        short_post: str,
        mode: str = 'smart',
        model: str = 'gpt-4o',
        settings: Optional[Dict] = None
    ) -> Dict:
        """
        Expand short post into full article.

        Args:
            short_post: User's short post text
            mode: 'smart' | 'research' | 'voice'
            model: OpenAI model to use
            settings: Dict of boolean flags from the UI toggles:
                {
                    'auto_research': bool,   # pull supporting data/context
                    'voice_matching': bool,  # lock to 4-part Dr.WinMac structure
                    'section_mapping': bool, # single unlabeled prose section
                    'smart_cta': bool,       # generate a closing-statement CTA
                }

        Returns:
            Dict with title, slug, lead, sections, teaser, cta, seo, date
        """
        settings = settings or {}
        logger.info(f"Expanding post | mode={mode} model={model} settings={settings}")

        # Step 1: Parse the short post
        parsed = self._parse_short_post(short_post)
        logger.info(f"Parsed topic: {parsed['topic']}")

        # Step 2: Research context — driven by mode AND auto_research toggle
        research_data = {}
        use_research = settings.get('auto_research', mode in ['smart', 'research'])
        if use_research:
            research_data = self._prepare_research_context(parsed['topic'], mode)
            logger.info("Research context prepared")

        # Step 3: Expand with OpenAI
        expanded = await self._expand_with_gpt4o(parsed, research_data, mode, model, settings)
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
        mode: str,
        model: str = 'gpt-4o',
        settings: Optional[Dict] = None
    ) -> Dict:
        """Use OpenAI to expand content in Dr.WinMac voice, driven by mode + settings flags."""

        settings = settings or {}
        use_voice_matching  = settings.get('voice_matching', False)
        use_section_mapping = settings.get('section_mapping', False)
        use_smart_cta       = settings.get('smart_cta', False)

        logger.info(f"Calling OpenAI {model} | mode={mode} voice={use_voice_matching} "
                    f"section_map={use_section_mapping} cta={use_smart_cta}")

        # ── Section structure instruction ──────────────────────────────────────
        if use_section_mapping:
            # Single unlabeled prose section — story-style
            section_instruction = (
                'Write a single flowing prose section with NO heading. '
                'Return exactly one entry in the sections array with an empty string heading "".'
            )
            sections_format = '[{"heading": "", "body": "full prose content here"}]'
        elif use_voice_matching:
            # Locked 4-part Dr.WinMac structure
            section_instruction = (
                'Use EXACTLY these four section headings in this order:\n'
                '1. "The Part Most People Aren\'t Watching"\n'
                '2. "What\'s Actually Changing"\n'
                '3. "Why This Actually Matters"\n'
                '4. "Where This Quietly Leads"'
            )
            sections_format = (
                '[{"heading": "The Part Most People Aren\'t Watching", "body": "1-2 paragraphs"},'
                '{"heading": "What\'s Actually Changing", "body": "2-3 paragraphs"},'
                '{"heading": "Why This Actually Matters", "body": "2-3 paragraphs"},'
                '{"heading": "Where This Quietly Leads", "body": "1-2 paragraphs"}]'
            )
        else:
            # Auto-Research mode or plain smart/voice: GPT chooses headings, 1-2 sections
            if mode == 'research' or settings.get('auto_research', False):
                section_instruction = (
                    'Write between 1 and 2 sections. Choose your own headings that best fit the topic. '
                    'Weave specific data points, named companies, and concrete figures into each section.'
                )
            elif mode == 'voice':
                section_instruction = (
                    'Write between 1 and 4 sections. Choose your own headings. '
                    'Focus entirely on voice, narrative flow and Dr.WinMac tone. No data citations needed.'
                )
            else:
                # smart (default)
                section_instruction = (
                    'Write between 2 and 4 sections. Choose your own headings. '
                    'Balance depth with readability, weaving in 2-3 supporting data points naturally.'
                )
            sections_format = '[{"heading": "Your chosen heading", "body": "paragraphs"}, ...]'

        # ── Voice profile (only injected when voice_matching is ON or mode != 'voice') ──
        if use_voice_matching or mode != 'voice':
            voice_block = self.voice_profile
        else:
            voice_block = (
                "VOICE: Calm, reflective, observational. "
                "Short-to-medium paragraphs. No hype. Sound like a thoughtful human observer."
            )

        # ── CTA instruction ────────────────────────────────────────────────────
        cta_instruction = (
            '\n- "cta": "A single closing statement that naturally invites the reader to take action '
            '(e.g. book a session, reach out, explore more). Keep it grounded and low-pressure."'
            if use_smart_cta else
            '\n- "cta": ""'
        )

        # ── Mode-specific depth note ───────────────────────────────────────────
        mode_notes = {
            'smart':    'Balance depth with readability. Include 2-3 supporting data points woven in naturally.',
            'research': 'Go deep. Include specific statistics, named companies, concrete figures, and dense sourcing throughout.',
            'voice':    'Rely entirely on voice and narrative. No data citations required. Be essayistic and reflective.',
        }
        mode_note = mode_notes.get(mode, mode_notes['smart'])

        # ── System prompt ──────────────────────────────────────────────────────
        system_prompt = f"""You are an AI content writer expanding a short blog post into a full article in the Dr.WinMac voice.

{voice_block}

EXPANSION MODE: {mode.upper()}
{mode_note}

SECTION STRUCTURE:
{section_instruction}

OUTPUT FORMAT — return valid JSON with exactly these fields:
{{
    "title": "Refined title",
    "seo_description": "1-2 sentence SEO summary",
    "lead": "Opening paragraph",
    "sections": {sections_format},{cta_instruction}
    "teaser": "One compelling sentence"
}}"""

        # ── User prompt ────────────────────────────────────────────────────────
        research_block = ""
        if research:
            areas = "\n".join(f"- {a}" for a in research.get('research_areas', []))
            depth = research.get('depth', 'balanced')
            note  = research.get('note', '')
            research_block = f"\nRESEARCH CONTEXT (depth={depth}):\n{areas}\nNote: {note}"

        user_prompt = f"""ORIGINAL POST:
{parsed['original_post']}

TOPIC: {parsed['topic']}{research_block}

Expand this into a full blog post. Return only valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2500
            )

            raw_content = None
            try:
                raw_content = response.choices[0].message.content
            except Exception:
                raw_content = getattr(response.choices[0].message, 'content', None) or getattr(response.choices[0], 'text', None)

            if raw_content is None:
                raise ValueError('No content returned from OpenAI')

            if isinstance(raw_content, (dict, list)):
                expanded = raw_content
            else:
                if isinstance(raw_content, bytes):
                    raw_content = raw_content.decode('utf-8')
                if isinstance(raw_content, str):
                    try:
                        expanded = json.loads(raw_content)
                    except json.JSONDecodeError:
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

            if not isinstance(expanded, dict):
                raise ValueError(f"Model returned JSON of unexpected type: {type(expanded)}")

            required = ['title', 'seo_description', 'lead', 'sections', 'teaser']
            missing = [f for f in required if f not in expanded]
            if missing:
                raise ValueError(f"Missing fields from model output: {', '.join(missing)}")

            # Ensure cta key always present
            if 'cta' not in expanded:
                expanded['cta'] = ''

            logger.info("GPT expansion successful")
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
            'cta': expanded.get('cta', ''),
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

    async def regenerate_content(
        self,
        title: str,
        lead: str,
        sections: list,
        teaser: str,
        model: str = 'gpt-4o',
        settings: Optional[Dict] = None,
        mode: str = 'smart'
    ) -> Dict:
        """
        Refine existing Lead, Sections and Teaser through the voice profile.
        Title, slug, SEO, date and image are NOT touched.
        Respects the same settings flags as expand_post.

        Returns a dict with keys: lead, sections, teaser, cta
        """
        settings = settings or {}
        use_voice_matching  = settings.get('voice_matching', False)
        use_section_mapping = settings.get('section_mapping', False)
        use_smart_cta       = settings.get('smart_cta', False)

        logger.info(f"Regenerating content for: {title!r} | model={model} settings={settings}")

        # Build mode-specific rewrite instruction
        if use_section_mapping:
            structure_note = (
                'Rewrite as a single flowing prose section with NO heading. '
                'Return exactly one entry in sections with an empty string heading "".'
            )
        elif use_voice_matching:
            structure_note = (
                'Preserve the exact four Dr.WinMac headings: '
                '"The Part Most People Aren\'t Watching", "What\'s Actually Changing", '
                '"Why This Actually Matters", "Where This Quietly Leads". Do not rename them.'
            )
        else:
            structure_note = 'Keep the same section headings exactly as given.'

        mode_notes = {
            'smart':    'Improve grammar, flow and clarity. Weave in 2-3 supporting data points naturally.',
            'research': 'Improve accuracy and depth. Add specific statistics and named sources where relevant.',
            'voice':    'Focus on voice, cadence and narrative flow. Remove any overly clinical phrasing.',
        }
        mode_note = mode_notes.get(mode, mode_notes['smart'])

        cta_instruction = (
            '- "cta": "A single closing statement inviting the reader to act — grounded, low-pressure."'
            if use_smart_cta else
            '- "cta": ""'
        )

        system_prompt = f"""You are an AI editor refining an existing Dr.WinMac blog post draft.

{self.voice_profile}

TASK ({mode.upper()} MODE):
- {mode_note}
- Preserve the approximate length of each field — do NOT significantly expand or shorten
- {structure_note}
- Maintain the Dr.WinMac voice throughout
- Do NOT change the topic, meaning or key facts

OUTPUT FORMAT — return valid JSON with these exact keys:
{{
    "lead": "refined lead paragraph",
    "sections": [
        {{"heading": "heading (or empty string)", "body": "refined body text"}},
        ...
    ],
    {cta_instruction}
    "teaser": "refined teaser sentence"
}}"""

        sections_text = '\n'.join(
            f'Section "{s.get("heading", "")}": {s.get("body", "")}'
            for s in sections
        )

        user_prompt = f"""TITLE (do not change): {title}

LEAD:
{lead}

SECTIONS:
{sections_text}

TEASER:
{teaser}

Refine the above content. Return only valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=2500
            )

            raw_content = response.choices[0].message.content
            if raw_content is None:
                raise ValueError('No content returned from OpenAI')
            if isinstance(raw_content, bytes):
                raw_content = raw_content.decode('utf-8')
            refined: Dict = json.loads(raw_content) if isinstance(raw_content, str) else dict(raw_content)

            required = ['lead', 'sections', 'teaser']
            missing = [f for f in required if f not in refined]
            if missing:
                raise ValueError(f"Missing fields from regenerate output: {', '.join(missing)}")

            if 'cta' not in refined:
                refined['cta'] = ''

            logger.info("Regeneration successful")
            return refined

        except Exception as e:
            logger.error(f"Regeneration failed: {e}")
            raise
