from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from managers.hierarchy_manager import HierarchyManager

class BaseWatcher(ABC):
    """Abstract base class for all knowledge ingestion watchers."""
    
    @abstractmethod
    async def watch(self, hierarchy: HierarchyManager) -> None:
        """
        Perform a single watch/ingest cycle.
        To be called by the MaintenanceManager.
        """
        pass
