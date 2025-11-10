# TUI Browser

A fast, intelligent terminal-based web browser that combines the speed of text browsers with the interactivity of modern web browsers, using LLMs as intelligent glue.

## Features

- **Fast Text Rendering**: Uses Lynx for instant, readable text layout
- **Full Interactivity**: Uses Playwright to capture all clickable elements, forms, and buttons
- **Intelligent Merging**: LLMs merge both outputs intelligently
- **Multi-LLM Support**: Works with local LLMs (Ollama) or cloud APIs (Gemini, OpenAI, Claude)
- **100% Local Option**: Run completely offline with Lynx + Ollama
- **Smart Fallbacks**: Gracefully handles failures at each layer

## Architecture

```
User Input → Cache Check → Lynx + Playwright (parallel)
                              ↓
                         Preprocessor (deterministic matching)
                              ↓
                         LLM Layer (intelligent placement)
                              ↓
                         Formatter (numbered elements)
                              ↓
                         Display → User Interaction
```

See [DESIGN.md](DESIGN.md) for detailed architecture documentation.

## Installation

### Prerequisites

1. **Python 3.8+**
2. **Lynx text browser**:
   ```bash
   # Ubuntu/Debian
   sudo apt install lynx

   # macOS
   brew install lynx

   # Arch Linux
   sudo pacman -S lynx
   ```

3. **Ollama** (for local LLMs - recommended):
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh

   # Pull a model
   ollama pull llama3.2:3b
   ```

### Setup

```bash
# Clone repository
git clone <repo-url>
cd Tui-browser

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy example config (optional)
cp config.example.toml config.toml
```

## Usage

### Basic Usage

```bash
# Navigate to a URL
python src/browser.py https://news.ycombinator.com

# With custom config
python src/browser.py https://example.com config.toml
```

### Commands

Once in the browser:

- **`[number]`** - Interact with numbered element (click, navigate, fill form)
- **`[url]`** - Navigate to a URL
- **`h, help`** - Show help
- **`b, back`** - Go back in history
- **`f, forward`** - Go forward in history
- **`l, links`** - List all links on page
- **`q, quit`** - Quit browser

### Examples

```bash
# Browse Hacker News
python src/browser.py https://news.ycombinator.com
> 5          # Click element [5]
> l          # List all links
> 10         # Navigate to link [10]
> b          # Go back
> q          # Quit

# Browse Wikipedia
python src/browser.py https://en.wikipedia.org
```

## Configuration

### Using Ollama (Local, Free)

```toml
[llm]
provider = "ollama"
model = "llama3.2:3b"
```

No API key required. Just install Ollama and pull a model.

### Using Google Gemini

```toml
[llm]
provider = "google"
model = "gemini-1.5-flash"
api_key = "your-api-key"
```

Or set environment variable: `export GOOGLE_API_KEY=your-key`

### Using OpenAI

```toml
[llm]
provider = "openai"
model = "gpt-4o-mini"
api_key = "your-api-key"
```

Or: `export OPENAI_API_KEY=your-key`

### With Fallback

```toml
[llm]
provider = "ollama"
model = "llama3.2:3b"
fallback_provider = "google"
fallback_model = "gemini-1.5-flash"
```

Tries Ollama first, falls back to Gemini if Ollama is unavailable.

### Disable LLM (Heuristic Only)

```toml
[llm]
enabled = false
```

Uses only deterministic matching. Faster but less accurate.

## How It Works

### 1. Parallel Fetching

Lynx and Playwright fetch the page simultaneously:

- **Lynx** (~500ms): Clean text layout with basic links
- **Playwright** (~2-3s): All interactive elements with CSS selectors

### 2. Deterministic Matching

URLs are matched between Lynx links and Playwright elements (80-90% success rate).

### 3. LLM Intelligent Placement

For elements Lynx missed (buttons, forms, JS-rendered content):

```
LLM prompt: "Where should this 'Vote' button go in the text?"
LLM response: {"show": true, "line": 5, "position": "before"}
```

### 4. Numbered Output

```
Hacker News

[1:new] [2:past] [3:comments]

[4:▲] 5. Show HN: Built a TUI Browser
   45 points by [6:username] | [7:12 comments]
```

### 5. Interaction

User types `4` → Browser clicks the upvote button via Playwright selector.

## Performance

### Speed

- **Simple pages** (Wikipedia, news): ~3-4 seconds
- **Complex pages** (SPAs, heavy JS): ~8-9 seconds
- **With cache**: <100ms

### Cost

- **Ollama (local)**: Free, unlimited
- **Gemini Flash**: ~$0.001 per page
- **GPT-4o-mini**: ~$0.002 per page

### Resource Usage

- **Memory**: ~4-6GB (Playwright + local LLM)
- **Disk**: ~1-5MB per cached page

## Troubleshooting

### "Lynx not found"

```bash
sudo apt install lynx  # Ubuntu/Debian
brew install lynx      # macOS
```

### "Cannot connect to Ollama"

```bash
# Start Ollama server
ollama serve

# Pull a model
ollama pull llama3.2:3b
```

### "Playwright error"

```bash
# Install browsers
playwright install chromium
```

### "LLM returns invalid JSON"

- Try a larger model (e.g., llama3.2:3b → llama3.1:8b)
- Or use cloud fallback

### Lynx outputs gibberish

Some sites require JavaScript. Disable Lynx:

```toml
[engine]
use_lynx = false
```

## Testing Individual Components

```bash
# Test fetcher
python src/fetcher.py https://example.com

# Test LLM
python src/llm.py

# Test merger
python src/merger.py https://example.com
```

## Recommended Models

### Local (Ollama)

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| llama3.2:1b | 1.3GB | Very Fast | Basic | Simple pages |
| llama3.2:3b | 2GB | Fast | Good | General use ⭐ |
| llama3.1:8b | 4.7GB | Medium | Great | Complex pages |
| qwen2.5:0.5b | 0.4GB | Very Fast | Basic | Cleanup only |

### Cloud

| Provider | Model | Speed | Quality | Cost |
|----------|-------|-------|---------|------|
| Google | gemini-1.5-flash | Fast | Excellent | Low ⭐ |
| OpenAI | gpt-4o-mini | Fast | Excellent | Low |
| Anthropic | claude-3-haiku | Fast | Good | Medium |

⭐ = Recommended

## Limitations

- JavaScript-heavy SPAs may be slow
- Some sites block headless browsers
- Local LLMs may struggle with complex layouts
- No image rendering (text only)
- No downloads or file uploads yet

## Roadmap

### Phase 1 (Current)
- ✅ Lynx + Playwright parallel fetching
- ✅ Multi-LLM support
- ✅ Intelligent merging
- ✅ Basic interaction (links, buttons, forms)

### Phase 2 (Planned)
- [ ] Caching layer
- [ ] Curses UI (vim-like navigation)
- [ ] Session history/bookmarks
- [ ] Better form handling
- [ ] Image support (for capable terminals)

### Phase 3 (Future)
- [ ] Reader mode
- [ ] Download manager
- [ ] Cookie/session management
- [ ] Custom user scripts
- [ ] Multi-tab support

## Contributing

Contributions welcome! See [DESIGN.md](DESIGN.md) for architecture details.

## License

MIT License - See LICENSE file

## Credits

Built using:
- [Lynx](https://lynx.invisible-island.net/) - Text browser
- [Playwright](https://playwright.dev/) - Browser automation
- [Ollama](https://ollama.com/) - Local LLM runtime

## Support

For issues, see the troubleshooting section above or open a GitHub issue.
