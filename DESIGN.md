# TUI Browser - Architecture Design Document

## Overview

A terminal-based web browser that combines the speed and readability of text browsers with the interactive capabilities of modern web browsers, using LLMs as intelligent glue between different rendering approaches.

## Core Philosophy

**The key insight:** Don't make the LLM do everything. Use specialized tools for what they're best at:
- **Lynx**: Fast, clean text layout
- **Playwright**: Complete interaction map and dynamic content
- **LLM**: Intelligent merging, semantic understanding, and ambiguity resolution

## Architecture Layers

```
┌─────────────────────────────────────────────────┐
│                  User Input                      │
│              (URL or element number)             │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              Cache Layer (Optional)              │
│         Check if page already processed          │
└────────────┬───────────────────┬────────────────┘
             │ MISS              │ HIT
             ▼                   ▼
      ┌─────────────┐      ┌──────────┐
      │   Fetcher   │      │  Return  │
      │   Layer     │      │  Cached  │
      └──────┬──────┘      └──────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌────────┐      ┌──────────┐
│  Lynx  │      │Playwright│
│        │      │          │
│ Fast   │      │ Complete │
│ Text   │      │ Map      │
└───┬────┘      └────┬─────┘
    │                │
    │   Text +       │  Elements +
    │   Links        │  Selectors +
    │                │  Content
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │  Preprocessor  │
    │                │
    │ 1. URL Match   │
    │ 2. Find Gaps   │
    │ 3. Categorize  │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │   LLM Layer    │◄─── Only for ambiguous cases
    │                │
    │ • Placement    │
    │ • Merging      │
    │ • Cleanup      │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │  Formatter     │
    │                │
    │ Inject numbers │
    │ Build mapping  │
    │ Final layout   │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │   Display to   │
    │     User       │
    └────────────────┘
```

## Layer 1: Fetcher (Parallel Execution)

### Lynx Fetcher

**Purpose:** Get clean, readable text layout with basic link extraction

**Execution:**
```bash
lynx -dump -width=80 -nolist [URL]
lynx -dump -listonly [URL]  # Separate call for link list
```

**Output:**
```
Text: Clean formatted text with visual layout preserved
Links: Numbered list of URLs [1], [2], [3]...
```

**Advantages:**
- Fast (< 500ms for most pages)
- Already formatted for terminal display
- Handles text flow well
- Minimal resource usage

**Limitations:**
- No JavaScript execution
- Misses dynamically loaded content
- Doesn't capture non-link interactive elements (buttons, forms)
- Poor handling of complex layouts (multi-column, tables)

### Playwright Fetcher

**Purpose:** Get complete interaction map and JavaScript-rendered content

**Execution:**
```javascript
// In browser context
const elements = [];
document.querySelectorAll('a, button, input, textarea, select, form').forEach((el, idx) => {
    const rect = el.getBoundingClientRect();
    elements.push({
        index: idx,
        type: el.tagName.toLowerCase(),
        text: el.innerText?.trim() || el.value || el.placeholder || '',
        href: el.href || null,
        selector: generateUniqueSelector(el),
        visible: rect.width > 0 && rect.height > 0,
        position: {
            top: rect.top,
            left: rect.left,
            documentOrder: getDocumentOrder(el)
        },
        attributes: { /* id, class, name, type, etc */ }
    });
});
```

**Output:**
```json
{
    "elements": [...],  // All interactive elements with selectors
    "content": "...",   // Full page content after JS execution
    "images": [...],    // Image metadata
    "forms": [...]      // Form structure
}
```

**Advantages:**
- Complete picture of all interactions
- Handles JavaScript-heavy sites
- Provides CSS selectors for clicking
- Can capture dynamic content

**Limitations:**
- Slower (2-3 seconds typical)
- Higher resource usage
- Raw data needs interpretation

### Parallel Execution Strategy

```python
with ThreadPoolExecutor() as executor:
    future_lynx = executor.submit(fetch_lynx, url)
    future_pw = executor.submit(fetch_playwright, url)

    lynx_result = future_lynx.result()  # Text + links
    pw_result = future_pw.result()      # Elements + content

# Total time = max(lynx_time, playwright_time)
# Typically ~2-3 seconds (Playwright bound)
```

## Layer 2: Preprocessor (Deterministic Matching)

### Phase 1: URL-Based Matching

**Goal:** Connect Lynx's numbered links to Playwright's selectors

```python
def match_by_url(lynx_links, pw_elements):
    """
    Lynx says: [1] -> https://example.com/page
    Playwright says: <a href="https://example.com/page"> has selector "nav > a:nth-child(1)"

    Result: mapping[1] = {url: "...", selector: "nav > a:nth-child(1)"}
    """
    mapping = {}

    for lynx_num, lynx_url in enumerate(lynx_links, start=1):
        for pw_el in pw_elements:
            if pw_el['type'] == 'a' and pw_el['href'] == lynx_url:
                mapping[lynx_num] = {
                    'url': lynx_url,
                    'selector': pw_el['selector'],
                    'text': pw_el['text'],
                    'type': 'link'
                }
                break

    return mapping
```

**Success rate:** ~80-90% for standard websites (all links get matched)

### Phase 2: Find Missing Elements

**Goal:** Identify what Lynx didn't capture

```python
def find_missing_elements(pw_elements, mapping):
    """
    Categories of missing elements:
    1. Buttons (not links)
    2. Form inputs
    3. JavaScript-rendered links
    4. Interactive elements (vote buttons, collapse, etc)
    """
    mapped_hrefs = {v['url'] for v in mapping.values() if 'url' in v}

    missing = []
    for el in pw_elements:
        if el['type'] in ['button', 'input', 'textarea', 'select']:
            # Lynx never shows these
            missing.append(el)
        elif el['type'] == 'a' and el['href'] not in mapped_hrefs:
            # Link that Lynx missed (JS-rendered, hidden, etc)
            missing.append(el)

    return missing
```

### Phase 3: Heuristic Categorization

**Goal:** Filter out noise before involving LLM

```python
def categorize_elements(elements):
    """
    Categories:
    - navigation: Top nav, menus (usually in header/nav tags)
    - primary: Main content interactions
    - secondary: Footer, share buttons, less critical
    - ignore: Ads, tracking, invisible elements
    """

    categories = {}

    for el in elements:
        # Rule-based filtering
        if not el['visible']:
            categories[el['index']] = 'ignore'
        elif el['text'] == '' and el['type'] != 'input':
            categories[el['index']] = 'ignore'
        elif 'ad' in el['selector'].lower() or 'track' in el['selector'].lower():
            categories[el['index']] = 'ignore'
        elif is_in_header(el):
            categories[el['index']] = 'navigation'
        elif is_in_footer(el):
            categories[el['index']] = 'secondary'
        else:
            # Needs LLM decision
            categories[el['index']] = 'unknown'

    return categories
```

**Result:** 60-70% of elements categorized without LLM

## Layer 3: LLM Layer (Intelligent Glue)

The LLM is called **only when necessary** for specific tasks:

### Task 1: Element Placement

**When:** Elements categorized as 'unknown' need placement decisions

**Input:**
```
LYNX TEXT (with line numbers):
1: Hacker News
2:
3: new | past | comments | ask | show | jobs | submit
4:
5: 1. Show HN: Built a TUI Browser (github.com)
6:    45 points by username 2 hours ago | 12 comments
7:
8: 2. Understanding Memory in Rust (blog.rust-lang.org)

ELEMENTS TO PLACE:
[
  {
    "id": "vote_0",
    "type": "button",
    "text": "▲",
    "near_text": "Show HN: Built",
    "selector": ".votearrow"
  },
  {
    "id": "hide_0",
    "type": "link",
    "text": "hide",
    "near_text": "12 comments",
    "selector": ".hide-link"
  }
]

For each element, decide:
1. Should it be shown? (yes/no)
2. Insert before or after which line number?
3. What format/label to use?

Return JSON only:
{
  "vote_0": {"show": true, "line": 5, "position": "before", "format": "[N:▲]"},
  "hide_0": {"show": true, "line": 6, "position": "after", "format": "[N:hide]"}
}
```

**Why LLM helps:**
- Understands semantic context ("vote button goes with article")
- Recognizes spatial relationships from text
- Filters truly irrelevant elements

**Model choice:** Local 3B model (llama3.2:3b via Ollama)
- Fast enough (~1-2 seconds)
- Good reasoning for simple placement
- Fallback to cloud (gemini-flash) if local unavailable

### Task 2: Dynamic Content Merging

**When:** Playwright captured JS-rendered content that Lynx showed as "Loading..."

**Input:**
```
LYNX OUTPUT:
Line 15: Comments
Line 16: Loading comments...
Line 17:

PLAYWRIGHT OUTPUT:
Comments section innerHTML:
<div class="comment">
  <span class="user">alice</span>: Great article!
</div>
<div class="comment">
  <span class="user">bob</span>: How does this work?
</div>

Task: Replace Lynx's "Loading comments..." with formatted Playwright content.
Return line numbers and replacement text.
```

**Output:**
```json
{
  "action": "replace",
  "start_line": 16,
  "end_line": 16,
  "replacement": "  alice: Great article!\n  bob: How does this work?"
}
```

**Model choice:** Local 3B or cloud depending on complexity

### Task 3: Format Cleanup (Optional)

**When:** Final output has formatting issues (rare)

**Input:**
```
Current text has these issues:
- Inconsistent spacing
- Duplicate elements
- Poor line breaks

Clean up formatting only. Do not change content or numbering.
```

**Model choice:** Tiny local model (qwen2.5:0.5b) - just formatting

## Layer 4: Formatter (Assembly)

### Inject Numbered Elements

```python
def inject_elements(lynx_text, missing_elements, placement_decisions, base_mapping):
    """
    Take the base Lynx text and inject missing elements at LLM-specified positions
    """

    lines = lynx_text.split('\n')
    next_num = max(base_mapping.keys()) + 1

    # Sort placements by line number (reverse to maintain line numbers)
    placements = sorted(placement_decisions.items(),
                       key=lambda x: x[1]['line'],
                       reverse=True)

    for el_id, decision in placements:
        if not decision['show']:
            continue

        line_num = decision['line']
        element = find_element_by_id(missing_elements, el_id)

        # Format: [N:label]
        marker = decision['format'].replace('N', str(next_num))

        if decision['position'] == 'before':
            lines[line_num] = marker + ' ' + lines[line_num]
        else:
            lines[line_num] = lines[line_num] + ' ' + marker

        # Add to mapping
        base_mapping[next_num] = {
            'selector': element['selector'],
            'type': element['type'],
            'text': element['text']
        }

        next_num += 1

    return '\n'.join(lines), base_mapping
```

### Build Final Mapping

**Structure:**
```python
mapping = {
    1: {
        'type': 'link',
        'url': 'https://example.com/page1',
        'selector': 'nav > a:nth-child(1)',
        'text': 'Home'
    },
    2: {
        'type': 'button',
        'selector': '.vote-button',
        'text': '▲',
        'action': 'click'  # vs 'navigate'
    },
    3: {
        'type': 'input',
        'selector': '#search-box',
        'text': 'Search',
        'action': 'fill'
    }
}
```

## Layer 5: User Interaction

```python
def handle_input(user_input, mapping, page):
    """
    User types a number or URL
    """

    if user_input.startswith('http'):
        # Direct URL navigation
        page.goto(user_input)
        return 'navigate'

    if not user_input.isdigit():
        print("Invalid input")
        return None

    num = int(user_input)

    if num not in mapping:
        print(f"Number {num} not found")
        return None

    element = mapping[num]

    # Route based on type
    if element['type'] == 'link':
        page.goto(element['url'])
        return 'navigate'

    elif element['type'] == 'button':
        page.click(element['selector'])
        page.wait_for_load_state('networkidle')
        return 'click'

    elif element['type'] == 'input':
        # Interactive input
        text = input(f"Enter {element['text']}: ")
        page.fill(element['selector'], text)
        return 'fill'

    elif element['type'] == 'submit':
        page.click(element['selector'])
        page.wait_for_load_state('networkidle')
        return 'submit'
```

## Special Cases

### Images

**Detection:**
```javascript
images = page.evaluate(() => {
    return Array.from(document.querySelectorAll('img')).map(img => ({
        src: img.src,
        alt: img.alt,
        width: img.width,
        height: img.height,
        visible: img.getBoundingClientRect().height > 0
    }));
});
```

**Display strategy:**
1. **Kitty/iTerm2:** Display inline using terminal image protocol
2. **Fallback:** Show as `[IMG: alt text]` with clickable number
3. **On click:** Open in external viewer (feh, imgcat, browser)

### Forms

**Detection:** Playwright finds all `<form>` elements and their inputs

**Display:**
```
=== Login Form ===
[23] Username: _____
[24] Password: _____ (hidden)
[25] [Submit]
```

**Interaction:**
- User types `23` -> prompt for username
- User types `24` -> prompt for password (hidden input)
- User types `25` -> submit form

### Tables

**Challenge:** Lynx linearizes tables poorly

**Solution:**
1. Playwright detects `<table>` elements
2. If found, render page to PDF
3. Extract table with pdfplumber (preserves structure)
4. Format as ASCII table or let LLM convert to readable text

### SPAs (Single Page Apps)

**Challenge:** Lynx shows nothing useful

**Detection:**
```python
def is_spa(html):
    indicators = [
        '<div id="root"></div>',
        '<div id="app"></div>',
        'React', 'Vue', 'Angular' in html,
        len(html) < 1000  # Minimal HTML, everything in JS
    ]
    return any(indicators)
```

**Fallback:** Use Playwright exclusively, skip Lynx entirely

## Configuration

### config.toml

```toml
[engine]
lynx_path = "/usr/bin/lynx"
use_lynx = true  # Set false to skip Lynx entirely
playwright_browser = "chromium"  # or "firefox", "webkit"

[llm]
provider = "ollama"  # or "openai", "anthropic", "google"
model = "llama3.2:3b"
fallback_provider = "google"
fallback_model = "gemini-1.5-flash"
api_key = ""  # For cloud providers

[llm.placement]
model = "llama3.2:3b"
provider = "ollama"

[llm.merging]
model = "llama3.2:3b"
provider = "ollama"

[llm.cleanup]
model = "qwen2.5:0.5b"
provider = "ollama"

[cache]
enabled = true
directory = "~/.cache/tui-browser"
ttl = 3600  # 1 hour

[display]
width = 80
show_images = true  # If terminal supports it
image_viewer = "auto"  # or "feh", "imgcat", etc

[performance]
parallel_fetch = true
timeout = 30000  # ms
```

## Performance Characteristics

### Speed Tiers

**Simple page (Wikipedia, news):**
- Lynx: 500ms
- Playwright: 2s
- Parallel: 2s (Playwright bound)
- LLM placement: 1-2s (local 3B)
- **Total: ~3-4s**

**Complex page (SPA, heavy JS):**
- Lynx: 500ms (but useless)
- Playwright: 5s
- Parallel: 5s
- LLM placement + merging: 3-4s
- **Total: ~8-9s**

**With cache hit:**
- **Total: <100ms**

### Resource Usage

**Memory:**
- Lynx: ~5MB
- Playwright: ~150-200MB
- Local LLM (3B): ~2-4GB RAM
- **Total: ~4-6GB** (acceptable for modern systems)

**Disk:**
- Cache: ~1-5MB per page
- Playwright browser: ~300MB (one-time)

## Error Handling

### Lynx Fails
- Fallback to Playwright-only mode
- Continue with reduced quality

### Playwright Fails
- Use Lynx output only
- Show warning: "Interactive elements may be incomplete"

### LLM Fails
- Use heuristic placement (insert at end)
- Continue with reduced quality
- Fallback to cloud LLM if available

### Network Timeout
- Retry with exponential backoff
- Show partial content if available

## Future Enhancements

### Phase 2
- Curses UI (vim-like navigation)
- Session history and back/forward
- Bookmarks
- Download manager

### Phase 3
- Reader mode (readability extraction)
- Custom CSS themes
- JavaScript console for debugging
- Screenshot capture

### Phase 4
- Multi-tab support
- Cookie/session management
- Basic ad blocking
- Custom user scripts

## Success Metrics

**Goal:** Fast, usable terminal browsing with full interactivity

**Targets:**
- 90% of pages render in <5 seconds
- 95% of interactive elements captured
- 100% reliable interaction (clicking, forms)
- Works offline with local LLM
- <$0.01 per page with cloud LLM

## Conclusion

This architecture leverages the strengths of each component:
- Lynx for speed and readability
- Playwright for completeness and interactivity
- LLM for intelligent integration

The result is a fast, cheap, and highly capable terminal browser that works with both modern and legacy websites.
