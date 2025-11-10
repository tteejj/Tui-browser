"""
Main TUI Browser with interaction handling
"""
import os
import sys
from typing import Optional, Dict
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, Page, Browser
import json

from fetcher import ParallelFetcher, LynxFetcher, PlaywrightFetcher
from llm import create_llm_manager, LLMManager
from merger import IntelligentMerger, ElementMapping, MergedResult


class InteractionHandler:
    """Handles user interactions with the browser"""

    def __init__(self, page: Page):
        self.page = page

    def handle_link(self, mapping: ElementMapping) -> str:
        """
        Navigate to a link

        Returns:
            'navigate' action performed
        """
        if mapping.url:
            if mapping.url.startswith('http'):
                self.page.goto(mapping.url, wait_until='networkidle', timeout=30000)
            else:
                # Relative URL
                full_url = urljoin(self.page.url, mapping.url)
                self.page.goto(full_url, wait_until='networkidle', timeout=30000)
        else:
            # Fallback: click the element
            self.page.click(mapping.selector, timeout=5000)
            self.page.wait_for_load_state('networkidle', timeout=30000)

        return 'navigate'

    def handle_button(self, mapping: ElementMapping) -> str:
        """
        Click a button

        Returns:
            'click' action performed
        """
        self.page.click(mapping.selector, timeout=5000)
        # Wait a bit for any page changes
        try:
            self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            # Page might not navigate, that's ok
            pass

        return 'click'

    def handle_input(self, mapping: ElementMapping) -> str:
        """
        Fill an input field

        Returns:
            'fill' action performed
        """
        # Prompt user for input
        label = mapping.text or "Input"
        user_input = input(f"\n{label}: ")

        # Fill the field
        self.page.fill(mapping.selector, user_input)

        return 'fill'

    def handle_submit(self, mapping: ElementMapping) -> str:
        """
        Submit a form

        Returns:
            'submit' action performed
        """
        self.page.click(mapping.selector, timeout=5000)
        self.page.wait_for_load_state('networkidle', timeout=30000)

        return 'submit'

    def handle_direct_url(self, url: str) -> str:
        """
        Navigate to a URL directly

        Returns:
            'navigate' action performed
        """
        if not url.startswith('http'):
            url = 'https://' + url

        self.page.goto(url, wait_until='networkidle', timeout=30000)
        return 'navigate'

    def handle_input_number(self, number: int, mapping_dict: Dict[int, ElementMapping]) -> Optional[str]:
        """
        Handle user entering a number

        Returns:
            Action performed or None if invalid
        """
        if number not in mapping_dict:
            print(f"❌ Number {number} not found")
            return None

        mapping = mapping_dict[number]

        try:
            if mapping.action == 'navigate' or mapping.type == 'link':
                return self.handle_link(mapping)
            elif mapping.action == 'click' or mapping.type == 'button':
                return self.handle_button(mapping)
            elif mapping.action == 'fill' or mapping.type in ['input', 'textarea', 'select']:
                return self.handle_input(mapping)
            elif mapping.action == 'submit':
                return self.handle_submit(mapping)
            else:
                print(f"⚠ Unknown action: {mapping.action}")
                return None
        except Exception as e:
            print(f"❌ Error handling element: {e}")
            return None


class TUIBrowser:
    """Main TUI Browser application"""

    def __init__(self, config: Dict):
        self.config = config
        self.llm_manager = create_llm_manager(config.get('llm', {}))

        # Setup fetcher
        use_lynx = config.get('engine', {}).get('use_lynx', True)
        self.fetcher = ParallelFetcher(use_lynx=use_lynx)

        # Setup merger
        use_llm = config.get('llm', {}).get('enabled', True)
        self.merger = IntelligentMerger(self.llm_manager, use_llm=use_llm)

        # Playwright browser (persistent)
        self.pw = None
        self.browser = None
        self.page = None
        self.interaction_handler = None

        # History
        self.history = []
        self.history_index = -1

    def start(self):
        """Start Playwright browser"""
        self.pw = sync_playwright().start()
        browser_type = self.config.get('engine', {}).get('playwright_browser', 'chromium')
        self.browser = getattr(self.pw, browser_type).launch(
            headless=self.config.get('engine', {}).get('headless', True)
        )
        self.page = self.browser.new_page()
        self.interaction_handler = InteractionHandler(self.page)

    def stop(self):
        """Stop browser"""
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()

    def navigate(self, url: str) -> MergedResult:
        """
        Navigate to URL and return merged result

        Args:
            url: URL to navigate to

        Returns:
            MergedResult with text and mapping
        """
        print(f"🌐 Navigating to {url}...")

        # Fetch with both tools
        print("📥 Fetching page (Lynx + Playwright)...")
        lynx_result, pw_result = self.fetcher.fetch(url)

        if not lynx_result.success:
            print(f"⚠ Lynx failed: {lynx_result.error}")
        if not pw_result.success:
            print(f"⚠ Playwright failed: {pw_result.error}")

        # Merge results
        print("🔗 Merging results...")
        result = self.merger.merge(lynx_result, pw_result)

        if result.success:
            # Add to history
            self.history.append(url)
            self.history_index = len(self.history) - 1

        return result

    def display(self, result: MergedResult):
        """Display merged result to user"""
        print("\n" + "=" * 80)
        print(f"URL: {self.page.url}")
        print("=" * 80 + "\n")
        print(result.text)
        print("\n" + "=" * 80)
        print(f"Interactive elements: {len(result.mapping)}")
        print("=" * 80)

    def show_help(self):
        """Show help message"""
        help_text = """
Commands:
  [number]  - Interact with numbered element
  [url]     - Navigate to URL
  h, help   - Show this help
  b, back   - Go back in history
  f, forward- Go forward in history
  l, links  - List all links
  q, quit   - Quit browser

Examples:
  5         - Click element [5]
  example.com - Navigate to example.com
  https://github.com - Navigate to GitHub
"""
        print(help_text)

    def list_links(self, mapping: Dict[int, ElementMapping]):
        """List all links"""
        links = [(num, m) for num, m in mapping.items() if m.type == 'link' or m.type == 'a']

        if not links:
            print("No links found")
            return

        print("\n=== Links ===")
        for num, mapping in sorted(links)[:50]:  # Show first 50
            url = mapping.url or "no url"
            text = mapping.text[:60] or "no text"
            print(f"  [{num}] {text}")
            print(f"       {url}")

    def run(self, initial_url: str):
        """
        Main browser loop

        Args:
            initial_url: URL to start with
        """
        try:
            self.start()

            # Navigate to initial URL
            result = self.navigate(initial_url)

            if not result.success:
                print(f"❌ Failed to load page: {result.error}")
                return

            # Main interaction loop
            while True:
                self.display(result)

                # Get user input
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ['q', 'quit', 'exit']:
                    print("👋 Goodbye!")
                    break

                elif user_input.lower() in ['h', 'help']:
                    self.show_help()
                    continue

                elif user_input.lower() in ['b', 'back']:
                    if self.history_index > 0:
                        self.history_index -= 1
                        url = self.history[self.history_index]
                        result = self.navigate(url)
                    else:
                        print("❌ No previous page")
                        continue

                elif user_input.lower() in ['f', 'forward']:
                    if self.history_index < len(self.history) - 1:
                        self.history_index += 1
                        url = self.history[self.history_index]
                        result = self.navigate(url)
                    else:
                        print("❌ No next page")
                        continue

                elif user_input.lower() in ['l', 'links']:
                    self.list_links(result.mapping)
                    continue

                # Handle number input
                elif user_input.isdigit():
                    num = int(user_input)
                    action = self.interaction_handler.handle_input_number(num, result.mapping)

                    if action in ['navigate', 'submit', 'click']:
                        # Page changed, re-fetch
                        current_url = self.page.url
                        result = self.navigate(current_url)
                    # else: input filled, continue with same page

                # Handle URL input
                elif user_input.startswith('http') or '.' in user_input:
                    self.interaction_handler.handle_direct_url(user_input)
                    current_url = self.page.url
                    result = self.navigate(current_url)

                else:
                    print(f"❌ Unknown command: {user_input}")
                    print("Type 'help' for commands")

        finally:
            self.stop()


def load_config(config_path: Optional[str] = None) -> Dict:
    """
    Load configuration from file or use defaults

    Args:
        config_path: Path to config file (optional)

    Returns:
        Configuration dictionary
    """
    default_config = {
        "engine": {
            "use_lynx": True,
            "playwright_browser": "chromium",
            "headless": True
        },
        "llm": {
            "enabled": True,
            "provider": "ollama",
            "model": "llama3.2:3b",
            "fallback_provider": None,
            "fallback_model": None
        },
        "display": {
            "width": 80
        }
    }

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                import tomli
                user_config = tomli.load(f)
                # Merge with defaults
                default_config.update(user_config)
        except Exception as e:
            print(f"⚠ Error loading config: {e}")
            print("Using default configuration")

    return default_config


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python browser.py <url> [config.toml]")
        print("\nExample:")
        print("  python browser.py https://news.ycombinator.com")
        print("  python browser.py https://example.com config.toml")
        sys.exit(1)

    url = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Load config
    config = load_config(config_path)

    print("🚀 TUI Browser Starting...")
    print(f"LLM: {config['llm']['provider']} / {config['llm']['model']}")
    print(f"Lynx: {'enabled' if config['engine']['use_lynx'] else 'disabled'}")
    print()

    # Run browser
    browser = TUIBrowser(config)
    browser.run(url)


if __name__ == "__main__":
    main()
