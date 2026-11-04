"""Core governance and optimization engines.
"""

from .compact import query_compact_state, set_compact_state
from .recycler import safe_recycle, DiskReconciliation
from .topology import get_system_reserved_files, get_partition_topology, get_drive_status
from .junction import scan_appdata, relocate_appdata
from .dev_cleaner import scan_dev_caches, clean_dev_caches, clean_playwright, clean_browsers
from .forensic import scan_system_components

__all__ = [
    "query_compact_state",
    "set_compact_state",
    "safe_recycle",
    "DiskReconciliation",
    "get_system_reserved_files",
    "get_partition_topology",
    "get_drive_status",
    "scan_appdata",
    "relocate_appdata",
    "scan_dev_caches",
    "clean_dev_caches",
    "clean_playwright",
    "clean_browsers",
    "scan_system_components",
]
