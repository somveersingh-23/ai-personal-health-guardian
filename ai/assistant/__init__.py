"""Assistant provider interface and built-in implementations."""

from .provider import AssistantProvider, StructuredPromptContext
from .template_provider import TemplateProvider

__all__ = ["AssistantProvider", "StructuredPromptContext", "TemplateProvider"]
