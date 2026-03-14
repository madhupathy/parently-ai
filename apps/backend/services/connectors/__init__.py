"""Platform connector adapters for Parently."""

from .base import BaseConnector
from .gdrive import GoogleDriveConnector
from .skyward import SkywardConnector
from .classdojo import ClassDojoConnector
from .brightwheel import BrightwheelConnector
from .gmail_connector import GmailConnector
from .openai_connector import OpenAIConnector

CONNECTORS = {
    "gmail": GmailConnector,
    "gdrive": GoogleDriveConnector,
    "skyward": SkywardConnector,
    "classdojo": ClassDojoConnector,
    "brightwheel": BrightwheelConnector,
    "openai": OpenAIConnector,
}

__all__ = [
    "BaseConnector",
    "GoogleDriveConnector",
    "SkywardConnector",
    "ClassDojoConnector",
    "BrightwheelConnector",
    "GmailConnector",
    "OpenAIConnector",
    "CONNECTORS",
]
