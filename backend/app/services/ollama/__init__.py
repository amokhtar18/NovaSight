"""
NovaSight Ollama Integration
=============================

Local LLM integration for natural language processing.
Implements ADR-002: No arbitrary code generation - LLM only generates
validated parameters for templates.
"""

from app.services.ollama.client import OllamaClient, OllamaError, OllamaConnectionError
from app.services.ollama.nl_to_params import NLToParametersService, QueryIntent
from app.services.ollama.prompt_templates import PromptTemplates
from app.services.ollama.query_classifier import (
    QueryClassifier,
    QueryType,
    ClassifiedIntent,
    QueryEntities,
    TimeRange,
)

__all__ = [
    # Client
    'OllamaClient',
    'OllamaError',
    'OllamaConnectionError',
    # NL-to-Parameters
    'NLToParametersService',
    'QueryIntent',
    'PromptTemplates',
    # Query Classifier
    'QueryClassifier',
    'QueryType',
    'ClassifiedIntent',
    'QueryEntities',
    'TimeRange',
]
