import os
import re
import shutil
from ..utils.system import format_size, get_dir_size, run_cmd, has_denied_descendant, is_junction_or_reparse
from .recycler import DiskReconciliation, safe_recycle

def scan_dev_caches():
    """Scan modern developer tools and AI caches."""
    user_home = os.path.expanduser("~")
    local_app_data = os.path.expandvars(r"%LOCALAPPDATA%")

    targets = [
        ("AI", "HuggingFace Hub Cache", os.path.join(user_home, ".cache", "huggingface", "hub")),
        ("AI", "Ollama Models", os.path.join(user_home, ".ollama", "models")),
        ("AI", "PyTorch Cache", os.path.join(user_home, ".cache", "torch")),
        ("Web", "NPM Global Cache", os.path.join(local_app_data, "npm-cache")),
        ("Web", "NPX Temporary Packages", os.path.join(local_app_data, "npm-cache", "_npx")),
        ("Web", "PNPM Store", os.path.join(local_app_data, "pnpm", "store")),
        ("Web", "Yarn Cache", os.path.join(local_app_data, "Yarn", "Cache")),
        ("Web", "Bun Cache", os.path.join(user_home, ".bun", "install", "cache")),
        ("Python", "uv Package Cache", os.path.join(local_app_data, "uv")),
        ("Python", "Pip Cache", os.path.join(local_app_data, "pip", "cache")),
        ("System", "Rust Cargo Registry", os.path.join(user_home, ".cargo", "registry")),
        ("System", "Go Build Cache", os.path.join(local_app_data, "go-build")),
        ("IDE", "Chrome Extension Dev Cache", os.path.join(local_app_data, "ChromeExtensionCache")),
    ]

    results = []
    total_bytes = 0
    print("=" * 70)
    print("【Modern AI & Developer Cache Radar】")
    print("=" * 70)
    print(f"{'Category':<10} | {'Tool / Ecosystem':<24} | {'Size':<10} | {'Path'}")
    print("-" * 75)

    for cat, label, p in targets:
        if os.path.exists(p):
            sz = get_dir_size(p)
            if sz > 1024 * 1024:
                total_bytes += sz
                results.append((cat, label, sz, p))
                print(f"{cat:<10} | {label:<24} | {format_size(sz):<10} | {p}")

    print("-" * 75)
    print(f"Total Developer Cache Found: {format_size(total_bytes)}\n")
    return results

def clean_dev_caches(dry_run=False):
    """Safely reconcile and clean dev caches (uv, npm, npx, pip, temp installers)."""
    print("=" * 70)
    print("【Developer Environment Cache Self-Healing】")
    if dry_run:
        print("⚠️ Mode: [Dry-Run Preview] (No files will be modified)")
    print("=" * 70)

    with DiskReconciliation("Developer Cache Cleanup", "C"):
        # 1. uv cache clean
        if dry_run:
            print("  [uv cache] (Dry-Run) Would execute: uv cache clean")
        else:
            out, err, code = run_cmd(["uv", "cache", "clean"])
            if code == 0:
                print(f"  [uv cache] Cleaned successfully.")

        # 2. npm & npx cache clean
        if dry_run:
            print("  [npm cache] (Dry-Run) Would execute: npm cache clean --force")
        else:
            out, err, code = run_cmd(["npm", "cache", "clean", "--force"])
            if code == 0:
                print("  [npm cache] Force purged.")

        # 3. Targeted npx purge
        local_app_data = os.path.expandvars(r"%LOCALAPPDATA%")
        npx_dir = os.path.join(local_app_data, "npm-cache", "_npx")
        if os.path.exists(npx_dir):
            sz = get_dir_size(npx_dir)
            if sz > 1024 * 1024:
                if dry_run:
                    print(f"  [_npx cache] (Dry-Run) Would clean: {format_size(sz)}")
                else:
                    safe_recycle(npx_dir, reason="NPX Temporary Cache Purge")

        # 4. pip cache purge
        if dry_run:
            print("  [pip cache] (Dry-Run) Would purge python pip caches")
        else:
            run_cmd(["python", "-m", "pip", "cache", "purge"])

        # 5. Installer leftovers & Updaters
        updater_dirs = []
        if os.path.exists(local_app_data):
            try:
                for item in os.listdir(local_app_data):
                    if item.endswith("-updater"):
                        updater_dirs.append(os.path.join(local_app_data, item))
            except Exception:
                pass

        known_updaters = [
            os.path.join(local_app_data, "Package Cache"),
            os.path.join(local_app_data, "Microsoft", "PowerToys", "Updates"),
            r"C:\Program Files (x86)\Google\GoogleUpdater\crx_cache",
        ]
        for ku in known_updaters:
            if ku not in updater_dirs and os.path.exists(ku):
                updater_dirs.append(ku)

        for u in updater_dirs:
            if os.path.exists(u):
                has_vhdx, _ = has_denied_descendant(u)
                if has_vhdx:
                    continue
                sz = get_dir_size(u)
                if sz > 1024 * 1024:
                    if dry_run:
                        print(f"  [Updater / Installer Cache] (Dry-Run) Would recycle: {os.path.basename(u)} ({format_size(sz)})")
                    else:
                        safe_recycle(u, reason="Installer Residual Cache")

        # 6. Temp Directory Non-locked Files
        temp_dir = os.path.join(local_app_data, "Temp")
        if os.path.exists(temp_dir):
            if dry_run:
                sz = get_dir_size(temp_dir)
                print(f"  [Temp Folder] (Dry-Run) Estimated recoverable non-locked temp files: ~{format_size(sz)}")
            else:
                freed = 0
                skipped = 0
                for item in os.listdir(temp_dir):
                    p = os.path.join(temp_dir, item)
                    try:
                        if is_junction_or_reparse(p):
                            continue
                        if os.path.isfile(p):
                            sz = os.path.getsize(p)
                            os.remove(p)
                            freed += sz
                        elif os.path.isdir(p):
                            has_vhdx, _ = has_denied_descendant(p)
                            if has_vhdx:
                                continue
                            sz = get_dir_size(p)
                            shutil.rmtree(p)
                            freed += sz
                    except Exception:
                        skipped += 1
                print(f"  [Temp Folder] Cleaned: released ~{format_size(freed)} (skipped {skipped} actively locked items)")

def clean_playwright(dry_run=False):
    """Retire and clean outdated Playwright browser binaries while preserving newest versions."""
    playwright_dir = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")
    if not os.path.exists(playwright_dir):
        print("Playwright directory not detected.")
        return

    print("=" * 70)
    print("【Playwright Browser Retirement & Cleanup】")
    if dry_run:
        print("⚠️ Mode: [Dry-Run Preview]")
    print("=" * 70)

    browser_groups = {}
    for item in os.listdir(playwright_dir):
        full_p = os.path.join(playwright_dir, item)
        if not os.path.isdir(full_p):
            continue
        m = re.match(r"^(chromium|firefox|webkit)-(\d+)$", item, re.IGNORECASE)
        if m:
            b_type = m.group(1).lower()
            b_ver = int(m.group(2))
            browser_groups.setdefault(b_type, []).append((b_ver, item, full_p))

    to_delete = []
    total_freed = 0

    for b_type, versions in browser_groups.items():
        versions.sort(key=lambda x: x[0], reverse=True)
        newest = versions[0]
        print(f"\nBrowser Engine: {b_type.upper()}")
        print(f"  [Keep] Active Version: {newest[1]}")

        for old_ver in versions[1:]:
            sz = get_dir_size(old_ver[2])
            total_freed += sz
            to_delete.append((old_ver[1], old_ver[2], sz))
            print(f"  [Retire] Old Version: {old_ver[1]} ({format_size(sz)})")

    if not to_delete:
        print("\nAll Playwright browser engines are up to date. No redundant versions found.")
        return

    if dry_run:
        print(f"\nEstimated Space to Free: {format_size(total_freed)}")
        return

    with DiskReconciliation("Playwright Browser Retirement", "C"):
        for name, p, sz in to_delete:
            try:
                shutil.rmtree(p)
                print(f"  🗑️ Removed retired version: {name} (Freed {format_size(sz)})")
            except Exception as e:
                print(f"  Failed to remove {name}: {e}")

def clean_browsers(dry_run=False):
    """Clean redundant historic EdgeCore versions while keeping active release."""
    edge_core = r"C:\Program Files (x86)\Microsoft\EdgeCore"
    if not os.path.exists(edge_core):
        print("EdgeCore directory not found.")
        return

    print("=" * 70)
    print("【Microsoft EdgeCore Historical Releases Cleanup】")
    if dry_run:
        print("⚠️ Mode: [Dry-Run Preview]")
    print("=" * 70)

    version_dirs = []
    for item in os.listdir(edge_core):
        p = os.path.join(edge_core, item)
        if os.path.isdir(p) and re.match(r"^\d+\.\d+\.\d+\.\d+$", item):
            version_dirs.append((item, p))

    if len(version_dirs) <= 1:
        print("EdgeCore has only one active version. No redundant releases found.")
        return

    def parse_ver(v_str):
        return [int(x) for x in v_str.split(".")]

    version_dirs.sort(key=lambda x: parse_ver(x[0]), reverse=True)
    newest = version_dirs[0]
    print(f"  [Keep] Active Version: {newest[0]}")

    to_clean = []
    total_sz = 0
    for old_v, p in version_dirs[1:]:
        sz = get_dir_size(p)
        total_sz += sz
        to_clean.append((old_v, p, sz))
        print(f"  [Retire] Redundant Version: {old_v} (~{format_size(sz)})")

    print(f"\nEstimated Space to Free: {format_size(total_sz)}")
    if dry_run:
        return

    for old_v, p, sz in to_clean:
        try:
            shutil.rmtree(p)
            print(f"  🗑️ Removed: {old_v}")
        except PermissionError:
            print(f"  Permission Denied: Removing {old_v} requires Administrator privileges.")
        except Exception as e:
            print(f"  Failed to remove {old_v}: {e}")
