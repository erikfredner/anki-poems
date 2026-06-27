"""Shared exception types for poetry-to-anki."""


class PoetryToAnkiError(Exception):
    """Base exception for poetry-to-anki errors."""


class FileProcessingError(PoetryToAnkiError):
    """Error occurred while processing a file."""


class ConfigurationError(PoetryToAnkiError):
    """Error in configuration validation."""


class AnkiConnectError(PoetryToAnkiError):
    """Error communicating with AnkiConnect."""
