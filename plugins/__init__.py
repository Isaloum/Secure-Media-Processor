"""
Secure Media Processor - Plugin Architecture

This module provides the plugin infrastructure for extending SMP
with domain-specific processors (medical imaging, video processing, etc.)

The core SMP package focuses on secure data transfer. Plugins add
specialized processing capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
import importlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata about a registered plugin."""
    name: str
    version: str
    description: str
    author: str
    requires_gpu: bool = False
    supported_formats: List[str] = field(default_factory=list)


class ProcessorPlugin(ABC):
    """
    Abstract base class for all SMP processor plugins.

    Plugins extend SMP's capabilities without modifying the core
    secure transfer pipeline. Each plugin processes data that has
    already been securely transferred to the local GPU workstation.

    Example:
        class CancerPredictionPlugin(ProcessorPlugin):
            def process(self, data, **kwargs):
                # Run cancer prediction on local GPU
                return predictions
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    def process(self, data: Any, **kwargs) -> Any:
        """
        Process data locally.

        Args:
            data: Input data (image, array, path, etc.)
            **kwargs: Plugin-specific options

        Returns:
            Processed output (predictions, transformed data, etc.)
        """
        pass

    def setup(self) -> None:
        """Initialize plugin resources (called once on registration)."""
        pass

    def teardown(self) -> None:
        """Clean up plugin resources."""
        pass

    def validate_input(self, data: Any) -> bool:
        """Validate that input data is acceptable for this plugin."""
        return True


class PluginRegistry:
    """
    Registry for managing processor plugins.

    The registry allows dynamic loading and management of plugins,
    enabling SMP to be extended without modifying core code.

    Example:
        registry = PluginRegistry()
        registry.register(MedicalImagingPlugin())

        # Process with specific plugin
        result = registry.process('medical-imaging', data)

        # Or auto-detect based on data type
        result = registry.auto_process(data)
    """

    def __init__(self):
        self._plugins: Dict[str, ProcessorPlugin] = {}
        self._format_mappings: Dict[str, str] = {}

    def register(self, plugin: ProcessorPlugin) -> None:
        """
        Register a processor plugin.

        Args:
            plugin: Plugin instance to register
        """
        name = plugin.metadata.name
        if name in self._plugins:
            logger.warning(f"Plugin '{name}' already registered, replacing")

        plugin.setup()
        self._plugins[name] = plugin

        # Map file formats to this plugin
        for fmt in plugin.metadata.supported_formats:
            self._format_mappings[fmt.lower()] = name

        logger.info(f"Registered plugin: {name} v{plugin.metadata.version}")

    def unregister(self, name: str) -> None:
        """Unregister a plugin by name."""
        if name in self._plugins:
            self._plugins[name].teardown()
            del self._plugins[name]
            # Clean up format mappings
            self._format_mappings = {
                k: v for k, v in self._format_mappings.items() if v != name
            }
            logger.info(f"Unregistered plugin: {name}")

    def get(self, name: str) -> Optional[ProcessorPlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> List[PluginMetadata]:
        """List all registered plugins."""
        return [p.metadata for p in self._plugins.values()]

    def process(self, plugin_name: str, data: Any, **kwargs) -> Any:
        """
        Process data with a specific plugin.

        Args:
            plugin_name: Name of the plugin to use
            data: Data to process
            **kwargs: Plugin-specific options

        Returns:
            Processed output

        Raises:
            KeyError: If plugin not found
            ValueError: If input validation fails
        """
        if plugin_name not in self._plugins:
            raise KeyError(f"Plugin '{plugin_name}' not registered")

        plugin = self._plugins[plugin_name]

        if not plugin.validate_input(data):
            raise ValueError(f"Input validation failed for plugin '{plugin_name}'")

        return plugin.process(data, **kwargs)

    def auto_process(self, data: Any, file_format: Optional[str] = None, **kwargs) -> Any:
        """
        Automatically select and run appropriate plugin based on data format.

        Args:
            data: Data to process
            file_format: Optional format hint (e.g., 'dcm', 'nii')
            **kwargs: Plugin-specific options

        Returns:
            Processed output

        Raises:
            ValueError: If no suitable plugin found
        """
        if file_format:
            fmt = file_format.lower().lstrip('.')
            if fmt in self._format_mappings:
                return self.process(self._format_mappings[fmt], data, **kwargs)

        # Try each plugin's validation
        for name, plugin in self._plugins.items():
            if plugin.validate_input(data):
                logger.info(f"Auto-selected plugin: {name}")
                return plugin.process(data, **kwargs)

        raise ValueError("No suitable plugin found for input data")


def load_plugin(module_path: str) -> Type[ProcessorPlugin]:
    """
    Dynamically load a plugin class from a module path.

    Args:
        module_path: Full path to plugin class (e.g., 'smp_medical.CancerPlugin')

    Returns:
        Plugin class (not instance)
    """
    module_name, class_name = module_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


# Global registry instance
_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _registry


def register_plugin(plugin: ProcessorPlugin) -> None:
    """Register a plugin with the global registry."""
    _registry.register(plugin)


def process_with_plugin(plugin_name: str, data: Any, **kwargs) -> Any:
    """Process data with a named plugin from the global registry."""
    return _registry.process(plugin_name, data, **kwargs)
