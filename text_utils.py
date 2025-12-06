# Text Processing Utilities

# This module provides utility functions for text processing.

def clean_text(text: str) -> str:
    """Removes unwanted characters from the text."""
    return ' '.join(text.split())


def count_words(text: str) -> int:
    """Counts the number of words in the text."""
    return len(text.split())


def to_lowercase(text: str) -> str:
    """Converts the text to lowercase."""
    return text.lower()