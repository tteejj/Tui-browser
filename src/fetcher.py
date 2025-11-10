"""
Fetcher module: Parallel fetching with Lynx and Playwright
"""
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Page, Browser
import re


@dataclass
class LynxResult:
    """Result from Lynx fetcher"""
    text: str
    links: List[Tuple[int, str]]  # [(link_number, url), ...]
    success: bool
    error: Optional[str] = None


@dataclass
class PlaywrightElement:
    """Single interactive element from Playwright"""
    index: int
    type: str  # 'a', 'button', 'input', etc.
    text: str
    href: Optional[str]
    selector: str
    visible: bool
    position: Dict[str, float]  # {top, left, documentOrder}
    attributes: Dict[str, str]


@dataclass
class PlaywrightResult:
    """Result from Playwright fetcher"""
    elements: List[PlaywrightElement]
    content: str  # Full page HTML after JS execution
    images: List[Dict]
    forms: List[Dict]
    success: bool
    error: Optional[str] = None


class LynxFetcher:
    """Fetch page content using Lynx text browser"""

    def __init__(self, lynx_path: str = "lynx", width: int = 80, timeout: int = 30):
        self.lynx_path = lynx_path
        self.width = width
        self.timeout = timeout

    def fetch(self, url: str) -> LynxResult:
        """
        Fetch URL with Lynx and extract text + links

        Returns:
            LynxResult with text content and numbered links
        """
        try:
            # Fetch text content (without link numbers in text)
            text_result = subprocess.run(
                [
                    self.lynx_path,
                    "-dump",
                    "-nolist",  # Don't show [1], [2] in text
                    f"-width={self.width}",
                    "-assume_charset=utf-8",
                    "-display_charset=utf-8",
                    url
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if text_result.returncode != 0:
                return LynxResult(
                    text="",
                    links=[],
                    success=False,
                    error=f"Lynx failed: {text_result.stderr}"
                )

            text = text_result.stdout

            # Fetch links separately
            links_result = subprocess.run(
                [
                    self.lynx_path,
                    "-dump",
                    "-listonly",  # Only output link list
                    "-nonumbers",  # Don't add numbers
                    url
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # Parse link list
            links = self._parse_links(links_result.stdout)

            return LynxResult(
                text=text,
                links=links,
                success=True
            )

        except subprocess.TimeoutExpired:
            return LynxResult(
                text="",
                links=[],
                success=False,
                error="Lynx timeout"
            )
        except FileNotFoundError:
            return LynxResult(
                text="",
                links=[],
                success=False,
                error="Lynx not found. Install with: apt install lynx"
            )
        except Exception as e:
            return LynxResult(
                text="",
                links=[],
                success=False,
                error=f"Lynx error: {str(e)}"
            )

    def _parse_links(self, link_output: str) -> List[Tuple[int, str]]:
        """
        Parse Lynx link list output

        Lynx -listonly output format:
        References

           1. https://example.com/page1
           2. https://example.com/page2
        """
        links = []
        # Match numbered links: "   1. https://..."
        pattern = r'^\s*(\d+)\.\s+(.+)$'

        for line in link_output.split('\n'):
            match = re.match(pattern, line)
            if match:
                num = int(match.group(1))
                url = match.group(2).strip()
                links.append((num, url))

        return links


class PlaywrightFetcher:
    """Fetch page interaction map using Playwright"""

    def __init__(self, browser_type: str = "chromium", headless: bool = True, timeout: int = 30000):
        self.browser_type = browser_type
        self.headless = headless
        self.timeout = timeout
        self.user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    def fetch(self, url: str) -> PlaywrightResult:
        """
        Fetch URL with Playwright and extract all interactive elements

        Returns:
            PlaywrightResult with elements, content, images, forms
        """
        try:
            with sync_playwright() as pw:
                browser = getattr(pw, self.browser_type).launch(headless=self.headless)
                page = browser.new_page(user_agent=self.user_agent)

                # Navigate to page
                page.goto(url, wait_until='networkidle', timeout=self.timeout)

                # Extract interactive elements
                elements = self._extract_elements(page)

                # Get full content
                content = page.content()

                # Extract images
                images = self._extract_images(page)

                # Extract forms
                forms = self._extract_forms(page)

                browser.close()

                return PlaywrightResult(
                    elements=elements,
                    content=content,
                    images=images,
                    forms=forms,
                    success=True
                )

        except Exception as e:
            return PlaywrightResult(
                elements=[],
                content="",
                images=[],
                forms=[],
                success=False,
                error=f"Playwright error: {str(e)}"
            )

    def _extract_elements(self, page: Page) -> List[PlaywrightElement]:
        """Extract all interactive elements from page"""

        # JavaScript to run in browser context
        js_code = """
        () => {
            function getSelector(element) {
                // Generate a unique CSS selector for element
                if (element.id) {
                    return '#' + element.id;
                }

                let path = [];
                while (element.parentElement) {
                    let selector = element.tagName.toLowerCase();
                    if (element.className) {
                        selector += '.' + element.className.trim().split(/\\s+/).join('.');
                    }

                    let sibling = element;
                    let nth = 1;
                    while (sibling.previousElementSibling) {
                        sibling = sibling.previousElementSibling;
                        if (sibling.tagName === element.tagName) nth++;
                    }
                    if (nth > 1) {
                        selector += ':nth-of-type(' + nth + ')';
                    }

                    path.unshift(selector);
                    element = element.parentElement;

                    // Limit depth
                    if (path.length >= 4) break;
                }

                return path.join(' > ');
            }

            function getDocumentOrder(element) {
                // Approximate position in document flow
                let rect = element.getBoundingClientRect();
                return rect.top * 10000 + rect.left;
            }

            const elements = [];
            const selector = 'a, button, input, textarea, select';

            document.querySelectorAll(selector).forEach((el, idx) => {
                const rect = el.getBoundingClientRect();
                const computedStyle = window.getComputedStyle(el);

                elements.push({
                    index: idx,
                    type: el.tagName.toLowerCase(),
                    text: (el.innerText || el.value || el.placeholder || '').trim().substring(0, 200),
                    href: el.href || null,
                    selector: getSelector(el),
                    visible: rect.width > 0 && rect.height > 0 && computedStyle.visibility !== 'hidden',
                    position: {
                        top: rect.top,
                        left: rect.left,
                        documentOrder: getDocumentOrder(el)
                    },
                    attributes: {
                        id: el.id || null,
                        className: el.className || null,
                        type: el.type || null,
                        name: el.name || null,
                        placeholder: el.placeholder || null
                    }
                });
            });

            return elements;
        }
        """

        elements_data = page.evaluate(js_code)

        # Convert to PlaywrightElement objects
        elements = []
        for el_data in elements_data:
            element = PlaywrightElement(
                index=el_data['index'],
                type=el_data['type'],
                text=el_data['text'],
                href=el_data['href'],
                selector=el_data['selector'],
                visible=el_data['visible'],
                position=el_data['position'],
                attributes=el_data['attributes']
            )
            elements.append(element)

        return elements

    def _extract_images(self, page: Page) -> List[Dict]:
        """Extract image metadata"""
        js_code = """
        () => {
            return Array.from(document.querySelectorAll('img')).map(img => {
                const rect = img.getBoundingClientRect();
                return {
                    src: img.src,
                    alt: img.alt,
                    width: img.width,
                    height: img.height,
                    visible: rect.height > 0 && rect.width > 0
                };
            });
        }
        """
        return page.evaluate(js_code)

    def _extract_forms(self, page: Page) -> List[Dict]:
        """Extract form structures"""
        js_code = """
        () => {
            return Array.from(document.querySelectorAll('form')).map(form => {
                const inputs = Array.from(form.querySelectorAll('input, textarea, select')).map(input => ({
                    type: input.type,
                    name: input.name,
                    placeholder: input.placeholder || '',
                    required: input.required
                }));

                return {
                    action: form.action,
                    method: form.method,
                    inputs: inputs
                };
            });
        }
        """
        return page.evaluate(js_code)


class ParallelFetcher:
    """Fetch with both Lynx and Playwright in parallel"""

    def __init__(self, lynx_fetcher: Optional[LynxFetcher] = None,
                 playwright_fetcher: Optional[PlaywrightFetcher] = None,
                 use_lynx: bool = True):
        self.lynx_fetcher = lynx_fetcher or LynxFetcher()
        self.playwright_fetcher = playwright_fetcher or PlaywrightFetcher()
        self.use_lynx = use_lynx

    def fetch(self, url: str, timeout: int = 45) -> Tuple[LynxResult, PlaywrightResult]:
        """
        Fetch URL with both tools in parallel

        Args:
            url: URL to fetch
            timeout: Overall timeout in seconds

        Returns:
            Tuple of (LynxResult, PlaywrightResult)
        """

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}

            if self.use_lynx:
                futures['lynx'] = executor.submit(self.lynx_fetcher.fetch, url)

            futures['playwright'] = executor.submit(self.playwright_fetcher.fetch, url)

            # Wait for both with timeout
            try:
                results = {}
                for name, future in futures.items():
                    try:
                        results[name] = future.result(timeout=timeout)
                    except TimeoutError:
                        if name == 'lynx':
                            results[name] = LynxResult("", [], False, "Timeout")
                        else:
                            results[name] = PlaywrightResult([], "", [], [], False, "Timeout")

                lynx_result = results.get('lynx', LynxResult("", [], False, "Lynx disabled"))
                playwright_result = results.get('playwright')

                return lynx_result, playwright_result

            except Exception as e:
                # Fallback on error
                return (
                    LynxResult("", [], False, str(e)),
                    PlaywrightResult([], "", [], [], False, str(e))
                )


def detect_spa(html: str) -> bool:
    """
    Detect if page is a Single Page App (SPA)

    SPAs typically have minimal HTML and rely on JavaScript
    """
    indicators = [
        '<div id="root"' in html,
        '<div id="app"' in html,
        'react' in html.lower(),
        'vue' in html.lower(),
        'angular' in html.lower(),
        len(html) < 1000  # Very minimal HTML
    ]

    return any(indicators)


if __name__ == "__main__":
    # Test the fetchers
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fetcher.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Fetching: {url}\n")

    fetcher = ParallelFetcher()
    lynx_result, pw_result = fetcher.fetch(url)

    print("=== LYNX RESULT ===")
    print(f"Success: {lynx_result.success}")
    if lynx_result.success:
        print(f"Text length: {len(lynx_result.text)} chars")
        print(f"Links found: {len(lynx_result.links)}")
        print(f"First 500 chars:\n{lynx_result.text[:500]}")
        print(f"\nFirst 5 links:")
        for num, link in lynx_result.links[:5]:
            print(f"  [{num}] {link}")
    else:
        print(f"Error: {lynx_result.error}")

    print("\n=== PLAYWRIGHT RESULT ===")
    print(f"Success: {pw_result.success}")
    if pw_result.success:
        print(f"Elements found: {len(pw_result.elements)}")
        print(f"Images found: {len(pw_result.images)}")
        print(f"Forms found: {len(pw_result.forms)}")
        print(f"\nFirst 5 elements:")
        for el in pw_result.elements[:5]:
            print(f"  [{el.index}] {el.type}: {el.text[:50]} ({'visible' if el.visible else 'hidden'})")
    else:
        print(f"Error: {pw_result.error}")
