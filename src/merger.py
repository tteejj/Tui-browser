"""
Intelligent merger: Combines Lynx + Playwright outputs using LLM as glue
"""
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from fetcher import LynxResult, PlaywrightResult, PlaywrightElement
from llm import LLMManager


@dataclass
class ElementMapping:
    """Maps numbered elements to their actions"""
    number: int
    type: str  # 'link', 'button', 'input', 'submit', 'image'
    text: str
    selector: Optional[str] = None
    url: Optional[str] = None
    action: str = 'navigate'  # or 'click', 'fill', 'submit'


@dataclass
class MergedResult:
    """Final merged output ready for display"""
    text: str
    mapping: Dict[int, ElementMapping]
    success: bool
    error: Optional[str] = None


class Preprocessor:
    """Deterministic preprocessing before LLM"""

    def match_by_url(self, lynx_links: List[Tuple[int, str]],
                     pw_elements: List[PlaywrightElement]) -> Dict[int, ElementMapping]:
        """
        Match Lynx's numbered links to Playwright selectors

        Returns:
            mapping[lynx_number] = ElementMapping
        """
        mapping = {}

        for num, url in lynx_links:
            # Find matching element in Playwright data
            for el in pw_elements:
                if el.type == 'a' and el.href == url:
                    mapping[num] = ElementMapping(
                        number=num,
                        type='link',
                        text=el.text or url,
                        selector=el.selector,
                        url=url,
                        action='navigate'
                    )
                    break

        return mapping

    def find_missing_elements(self, pw_elements: List[PlaywrightElement],
                              mapping: Dict[int, ElementMapping]) -> List[PlaywrightElement]:
        """
        Find interactive elements that Lynx missed

        Returns:
            List of elements not in mapping
        """
        mapped_hrefs = {m.url for m in mapping.values() if m.url}

        missing = []
        for el in pw_elements:
            # Skip invisible elements
            if not el.visible:
                continue

            # Skip elements with no text and not input
            if not el.text and el.type != 'input':
                continue

            # Buttons are always missing from Lynx
            if el.type in ['button', 'input', 'textarea', 'select']:
                missing.append(el)

            # Links that Lynx missed
            elif el.type == 'a' and el.href not in mapped_hrefs:
                missing.append(el)

        return missing

    def categorize_elements(self, elements: List[PlaywrightElement]) -> Dict[int, str]:
        """
        Categorize elements using heuristics

        Categories: 'navigation', 'primary', 'secondary', 'ignore', 'unknown'
        """
        categories = {}

        for el in elements:
            # Rule-based categorization
            selector_lower = el.selector.lower()
            text_lower = el.text.lower()

            # Ignore ads, tracking
            if any(x in selector_lower for x in ['ad', 'track', 'analytics', 'pixel']):
                categories[el.index] = 'ignore'

            # Navigation elements
            elif any(x in selector_lower for x in ['nav', 'header', 'menu']):
                categories[el.index] = 'navigation'

            # Footer elements
            elif any(x in selector_lower for x in ['footer', 'copyright']):
                categories[el.index] = 'secondary'

            # Empty text (but visible input might be important)
            elif not el.text and el.type != 'input':
                categories[el.index] = 'ignore'

            # Small buttons with symbols (vote, collapse, etc)
            elif el.type == 'button' and len(el.text) < 3:
                categories[el.index] = 'unknown'  # Let LLM decide

            # Forms and inputs are primary
            elif el.type in ['input', 'textarea', 'select']:
                categories[el.index] = 'primary'

            # Everything else needs LLM
            else:
                categories[el.index] = 'unknown'

        return categories


class LLMPlacer:
    """Uses LLM to place missing elements in Lynx text"""

    def __init__(self, llm_manager: LLMManager):
        self.llm = llm_manager

    def place_elements(self, lynx_text: str, elements: List[PlaywrightElement]) -> Dict[int, Dict]:
        """
        Ask LLM to decide where to place missing elements

        Returns:
            {element_index: {show: bool, line: int, position: 'before'|'after', format: str}}
        """
        # Add line numbers to text
        lines = lynx_text.split('\n')
        numbered_lines = '\n'.join(f"{i}: {line}" for i, line in enumerate(lines))

        # Format elements for LLM
        elements_json = []
        for el in elements:
            elements_json.append({
                "id": f"el_{el.index}",
                "type": el.type,
                "text": el.text[:100],  # Truncate long text
                "visible": el.visible
            })

        system_prompt = """You are helping to integrate interactive web elements into a text layout.
Your job is to decide:
1. Should the element be shown? (ignore ads, tracking, irrelevant elements)
2. Where should it go? (which line number)
3. How should it be formatted? (use [N:label] format)

Be conservative - only show elements that are clearly useful for navigation or interaction."""

        prompt = f"""LYNX TEXT (with line numbers):
{numbered_lines[:3000]}

ELEMENTS TO PLACE:
{json.dumps(elements_json, indent=2)}

For each element, decide placement. Return JSON only:
{{
  "el_0": {{"show": true, "line": 5, "position": "before", "format": "[N:▲]"}},
  "el_1": {{"show": false, "reason": "tracking pixel"}},
  ...
}}

Use "N" as placeholder for the number - it will be replaced.
Position can be "before" or "after" the line.
"""

        response = self.llm.generate_json(prompt, system_prompt, temperature=0.3, max_tokens=2000)

        # Handle errors
        if "error" in response:
            print(f"⚠ LLM placement failed: {response['error']}")
            # Return empty placements
            return {}

        # Convert el_X keys back to indices
        placements = {}
        for key, value in response.items():
            if key.startswith("el_"):
                try:
                    idx = int(key.split("_")[1])
                    placements[idx] = value
                except (IndexError, ValueError):
                    continue

        return placements

    def merge_dynamic_content(self, lynx_text: str, pw_content: str) -> str:
        """
        Merge JavaScript-rendered content into Lynx text

        This handles cases where Lynx shows "Loading..." but Playwright has the real content
        """

        # Check if there are obvious loading indicators
        loading_indicators = ['loading...', 'please wait', 'loading content']

        has_loading = any(indicator in lynx_text.lower() for indicator in loading_indicators)

        if not has_loading:
            # No merging needed
            return lynx_text

        system_prompt = """You are merging dynamic content that loaded via JavaScript into a static text view.
The static view shows "Loading..." but the dynamic view has the real content.
Replace loading indicators with the actual content, maintaining the text layout."""

        prompt = f"""STATIC TEXT (from Lynx):
{lynx_text[:2000]}

DYNAMIC CONTENT (from Playwright, may be HTML):
{pw_content[:2000]}

Replace any "loading..." sections with the actual content.
Return the merged text maintaining the same format and layout."""

        response = self.llm.generate(prompt, system_prompt, temperature=0.3, max_tokens=2000)

        if response.success:
            return response.text
        else:
            # Fallback: return original
            return lynx_text


class Formatter:
    """Assembles final output with numbered elements"""

    def inject_elements(self, lynx_text: str, missing_elements: List[PlaywrightElement],
                       placements: Dict[int, Dict], base_mapping: Dict[int, ElementMapping]) -> Tuple[str, Dict]:
        """
        Inject missing elements into Lynx text

        Returns:
            (enhanced_text, full_mapping)
        """
        lines = lynx_text.split('\n')
        next_num = max(base_mapping.keys()) + 1 if base_mapping else 1

        # Sort placements by line number (reverse to preserve line numbers)
        placement_items = [
            (el_idx, decision)
            for el_idx, decision in placements.items()
            if decision.get('show', False)
        ]
        placement_items.sort(key=lambda x: x[1].get('line', 0), reverse=True)

        new_mapping = base_mapping.copy()

        for el_idx, decision in placement_items:
            # Find the element
            element = next((el for el in missing_elements if el.index == el_idx), None)
            if not element:
                continue

            line_num = decision.get('line', 0)
            if line_num >= len(lines):
                line_num = len(lines) - 1

            # Format: [N:label]
            format_str = decision.get('format', '[N:button]')
            marker = format_str.replace('N', str(next_num))

            # Insert
            position = decision.get('position', 'after')
            if position == 'before':
                lines[line_num] = marker + ' ' + lines[line_num]
            else:
                lines[line_num] = lines[line_num] + ' ' + marker

            # Add to mapping
            action = 'navigate' if element.type == 'a' else 'click'
            if element.type in ['input', 'textarea']:
                action = 'fill'
            elif element.type == 'button' and 'submit' in element.text.lower():
                action = 'submit'

            new_mapping[next_num] = ElementMapping(
                number=next_num,
                type=element.type,
                text=element.text,
                selector=element.selector,
                url=element.href,
                action=action
            )

            next_num += 1

        return '\n'.join(lines), new_mapping


class IntelligentMerger:
    """Main merger class that combines all layers"""

    def __init__(self, llm_manager: LLMManager, use_llm: bool = True):
        self.preprocessor = Preprocessor()
        self.placer = LLMPlacer(llm_manager) if use_llm else None
        self.formatter = Formatter()
        self.use_llm = use_llm

    def merge(self, lynx_result: LynxResult, pw_result: PlaywrightResult) -> MergedResult:
        """
        Main merge function

        Steps:
        1. URL-based matching (deterministic)
        2. Find missing elements
        3. Categorize elements (heuristic)
        4. LLM placement for unknown elements
        5. Inject and format
        """

        # Handle failures
        if not lynx_result.success and not pw_result.success:
            return MergedResult(
                text="",
                mapping={},
                success=False,
                error="Both Lynx and Playwright failed"
            )

        # Fallback: Use only Playwright if Lynx failed
        if not lynx_result.success:
            return self._playwright_only_fallback(pw_result)

        # Step 1: URL matching
        base_mapping = self.preprocessor.match_by_url(lynx_result.links, pw_result.elements)

        # Step 2: Find missing elements
        missing = self.preprocessor.find_missing_elements(pw_result.elements, base_mapping)

        if not missing:
            # No missing elements, return Lynx output as-is
            return MergedResult(
                text=lynx_result.text,
                mapping=base_mapping,
                success=True
            )

        # Step 3: Categorize
        categories = self.preprocessor.categorize_elements(missing)

        # Filter to only unknown elements that need LLM
        unknown_elements = [el for el in missing if categories.get(el.index) == 'unknown']

        # Step 4: LLM placement
        placements = {}
        if self.use_llm and self.placer and unknown_elements:
            placements = self.placer.place_elements(lynx_result.text, unknown_elements)

        # Also add deterministically categorized elements
        primary_elements = [el for el in missing if categories.get(el.index) == 'primary']
        for el in primary_elements:
            # Place primary elements at the end (simple heuristic)
            placements[el.index] = {
                'show': True,
                'line': len(lynx_result.text.split('\n')) - 1,
                'position': 'after',
                'format': f'[N:{el.type}]'
            }

        # Step 5: Inject elements
        enhanced_text, full_mapping = self.formatter.inject_elements(
            lynx_result.text,
            missing,
            placements,
            base_mapping
        )

        return MergedResult(
            text=enhanced_text,
            mapping=full_mapping,
            success=True
        )

    def _playwright_only_fallback(self, pw_result: PlaywrightResult) -> MergedResult:
        """
        Fallback when Lynx fails: use Playwright content

        Extract text from HTML and number all interactive elements
        """
        # Simple HTML to text (very basic)
        from html import unescape
        import re

        html = pw_result.content
        # Remove scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode HTML entities
        text = unescape(text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        text = '\n'.join(text[i:i+80] for i in range(0, len(text), 80))  # Wrap at 80 chars

        # Number visible elements
        mapping = {}
        for i, el in enumerate(pw_result.elements[:50], start=1):  # Limit to first 50
            if el.visible:
                action = 'navigate' if el.type == 'a' else 'click'
                if el.type in ['input', 'textarea']:
                    action = 'fill'

                mapping[i] = ElementMapping(
                    number=i,
                    type=el.type,
                    text=el.text[:50],
                    selector=el.selector,
                    url=el.href,
                    action=action
                )

                # Append to text
                text += f"\n[{i}] {el.text[:50]}"

        return MergedResult(
            text=text,
            mapping=mapping,
            success=True
        )


if __name__ == "__main__":
    # Test merger
    import sys
    from fetcher import ParallelFetcher
    from llm import create_llm_manager

    if len(sys.argv) < 2:
        print("Usage: python merger.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Fetching and merging: {url}\n")

    # Fetch
    fetcher = ParallelFetcher()
    lynx_result, pw_result = fetcher.fetch(url)

    # Setup LLM
    llm_config = {
        "provider": "ollama",
        "model": "llama3.2:3b"
    }
    llm_manager = create_llm_manager(llm_config)

    # Merge
    merger = IntelligentMerger(llm_manager, use_llm=True)
    result = merger.merge(lynx_result, pw_result)

    print("=== MERGED RESULT ===")
    print(f"Success: {result.success}")
    if result.success:
        print(f"\nText:\n{result.text[:1000]}")
        print(f"\nMapping ({len(result.mapping)} elements):")
        for num, mapping in sorted(result.mapping.items())[:10]:
            print(f"  [{num}] {mapping.type}: {mapping.text[:50]}")
    else:
        print(f"Error: {result.error}")
