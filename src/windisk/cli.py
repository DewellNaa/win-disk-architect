import sys
import argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .core.topology import get_drive_status, get_system_reserved_files, get_partition_topology
from .core.compact import query_compact_state, set_compact_state
from .core.dev_cleaner import scan_dev_caches, clean_dev_caches, clean_playwright, clean_browsers
from .core.junction import scan_appdata, relocate_appdata
from .core.forensic import scan_system_components
from .core.recycler import safe_recycle
from .utils.system import is_admin, format_size, run_cmd

BANNER = r"""
 __      ___       _____  _     _      __  __           _     _ _            _   
 \ \    / (_)     |  __ \(_)   | |    |  \/  |         | |   (_) |          | |  
  \ \  / / _ _ __ | |  | |_ ___| | __ | \  / | __ _ ___| |_   _| |_ ___  ___| |_ 
   \ \/ / | | '_ \| |  | | / __| |/ / | |\/| |/ _` / __| __| | | __/ _ \/ __| __|
    \  /  | | | | | |__| | \__ \   <  | |  | | (_| \__ \ |_  | | ||  __/ (__| |_ 
     \/   |_|_| |_|_____/|_|___/_|\_\ |_|  |_|\__,_|___/\__| |_|\__\___|\___|\__|
            Windows System Drive Architecture Optimizer (v1.0.0)
"""

def cmd_diagnose(full=False):
    print(BANNER)
    print("=" * 70)
    print("【1. Logical Drive Capacity & Utilization】")
    print("=" * 70)
    ps_cmd = (
        "Get-PSDrive -PSProvider FileSystem | Select-Object Root, "
        "@{N='UsedGB';E={[math]::Round($_.Used/1GB,2)}}, "
        "@{N='FreeGB';E={[math]::Round($_.Free/1GB,2)}}, "
        "@{N='FreeRatio%';E={[math]::Round(($_.Free/($_.Used+$_.Free))*100,1)}} | "
        "Format-Table -AutoSize | Out-String"
    )
    out, _, _ = run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd])
    print(out)

    print("=" * 70)
    print("【2. Operating System Reserved Storage Files】")
    print("=" * 70)
    files = get_system_reserved_files()
    for f in files:
        status_tag = f"[{f['status'].upper():<7}]"
        print(f"  {status_tag} {f['path']:<20} Size: {f['size_str']}")

    print("\n=" * 70)
    print("【3. Windows CompactOS Transparent Compression】")
    print("=" * 70)
    is_compact, msg = query_compact_state()
    state_str = "ENABLED (Compressing OS binaries, saving 3~5 GB)" if is_compact else "DISABLED (Can be enabled with `windisk compact on`)"
    print(f"  Current Status: {state_str}")

    print("\n=" * 70)
    print("【4. Physical Disk & Partition Hardware Topology】")
    print("=" * 70)
    top_out = get_partition_topology()
    print(top_out)

    if full:
        scan_system_components()
        scan_dev_caches()
        scan_appdata(min_size_mb=300)

def cmd_compact(action):
    if action == "query":
        _, msg = query_compact_state()
        print(msg)
    elif action == "on":
        if not is_admin():
            print("Administrator privileges required. Please run terminal as Administrator.")
            sys.exit(1)
        print("Enabling CompactOS transparent compression...")
        ok, msg = set_compact_state(True)
        print(msg)
    elif action == "off":
        if not is_admin():
            print("Administrator privileges required. Please run terminal as Administrator.")
            sys.exit(1)
        print("Disabling CompactOS compression...")
        ok, msg = set_compact_state(False)
        print(msg)

def main():
    parser = argparse.ArgumentParser(
        description="WinDiskArchitect: Windows System Drive Architecture Optimizer & Non-destructive Space Governance",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command")

    # diagnose
    diag_p = subparsers.add_parser("diagnose", help="Comprehensive system storage and topology diagnosis")
    diag_p.add_argument("--full", action="store_true", help="Expand deep components, developer caches, and AppData radar")

    # clean
    clean_p = subparsers.add_parser("clean", help="Safely clean developer caches, temp files, and updater residues")
    clean_p.add_argument("--dry-run", action="store_true", help="Preview estimated space recovery without deletion")

    # compact
    compact_p = subparsers.add_parser("compact", help="Manage Windows CompactOS transparent compression")
    compact_p.add_argument("action", choices=["query", "on", "off"], default="query", nargs="?", help="CompactOS action")

    # relocate
    reloc_p = subparsers.add_parser("relocate", help="Seamlessly move large AppData directory to non-system drive with Junction")
    reloc_p.add_argument("path", help="Path of the AppData directory to relocate")
    reloc_p.add_argument("--dst-root", help="Destination root directory (defaults to largest non-system partition)")

    # scan-appdata
    appdata_p = subparsers.add_parser("scan-appdata", help="Radar scan for bloated directories in AppData")
    appdata_p.add_argument("--min-size-mb", type=float, default=300, help="Minimum directory size filter in MB (default: 300)")

    # scan-dev
    subparsers.add_parser("scan-dev", help="Scan modern AI and developer caches (npm, uv, pip, huggingface, etc.)")

    # scan-system
    subparsers.add_parser("scan-system", help="Scan deep Windows components (WinSxS, DriverStore, Crash Dumps)")

    # clean-playwright
    pw_p = subparsers.add_parser("clean-playwright", help="Retire outdated Playwright browser binaries")
    pw_p.add_argument("--dry-run", action="store_true", help="Preview without deleting")

    # clean-browsers
    br_p = subparsers.add_parser("clean-browsers", help="Clean redundant historical EdgeCore versions")
    br_p.add_argument("--dry-run", action="store_true", help="Preview without deleting")

    # safe-recycle
    rc_p = subparsers.add_parser("safe-recycle", help="Move target safely to native Windows Recycle Bin with memo")
    rc_p.add_argument("path", help="Target path to recycle")
    rc_p.add_argument("--reason", default="Manual Cleanup", help="Reason for record in memo file")

    args = parser.parse_args()

    if args.command == "diagnose":
        cmd_diagnose(full=args.full)
    elif args.command == "clean":
        clean_dev_caches(dry_run=args.dry_run)
    elif args.command == "compact":
        cmd_compact(args.action)
    elif args.command == "relocate":
        relocate_appdata(args.path, args.dst_root)
    elif args.command == "scan-appdata":
        scan_appdata(min_size_mb=args.min_size_mb)
    elif args.command == "scan-dev":
        scan_dev_caches()
    elif args.command == "scan-system":
        scan_system_components()
    elif args.command == "clean-playwright":
        clean_playwright(dry_run=args.dry_run)
    elif args.command == "clean-browsers":
        clean_browsers(dry_run=args.dry_run)
    elif args.command == "safe-recycle":
        safe_recycle(args.path, reason=args.reason)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
