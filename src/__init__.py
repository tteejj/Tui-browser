"""
TUI Browser - Terminal-based web browser with intelligent LLM integration
"""

__version__ = "0.1.0"

from .fetcher import ParallelFetcher, LynxFetcher, PlaywrightFetcher
from .llm import LLMManager, create_llm_manager
from .merger import IntelligentMerger
from .browser import TUIBrowser

__all__ = [
    'ParallelFetcher',
    'LynxFetcher',
    'PlaywrightFetcher',
    'LLMManager',
    'create_llm_manager',
    'IntelligentMerger',
    'TUIBrowser',
]
