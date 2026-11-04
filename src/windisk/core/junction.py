import os
import shutil
from ..utils.system import (
    format_size,
    get_dir_size,
    run_cmd,
    is_junction_or_reparse,
    has_denied_descendant,
    get_largest_free_drive
)
from .recycler import DiskReconciliation

def scan_appdata(min_size_mb=300):
    """Scan Local and Roaming AppData directories larger than min_size_mb."""
    user_home = os.path.expanduser("~")
    local_dir = os.path.join(user_home, "AppData", "Local")
    roaming_dir = os.path.join(user_home, "AppData", "Roaming")

    print("=" * 75)
    print("【AppData Large Directory Radar】")
    print(f"Threshold: >= {min_size_mb} MB")
    print("=" * 75)

    candidates = []
    min_size_bytes = int(min_size_mb * 1024 * 1024)

    for scope, base_dir in [("Local", local_dir), ("Roaming", roaming_dir)]:
        if not os.path.exists(base_dir):
            continue
        try:
            with os.scandir(base_dir) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        is_junc = is_junction_or_reparse(entry)
                        sz = 0 if is_junc else get_dir_size(entry.path, max_depth=3)
                        if is_junc or sz >= min_size_bytes:
                            candidates.append({
                                "name": entry.name,
                                "scope": scope,
                                "path": entry.path,
                                "size_bytes": sz,
                                "is_junction": is_junc
                            })
        except Exception:
            pass

    candidates.sort(key=lambda x: x["size_bytes"], reverse=True)

    print(f"{'Index':<5} | {'Scope':<8} | {'Directory Name':<28} | {'Size':<10} | {'Status'}")
    print("-" * 75)
    for i, c in enumerate(candidates, 1):
        status = "🔗 Junction Link" if c["is_junction"] else "📁 Local Directory"
        print(f"#{i:<4} | {c['scope']:<8} | {c['name']:<28} | {format_size(c['size_bytes']):<10} | {status}")
    print("-" * 75)
    return candidates

def relocate_appdata(src_path, dst_root=None):
    """Safely relocate an AppData directory to another partition and establish an NTFS Junction link."""
    src_path = os.path.abspath(src_path)
    if not os.path.exists(src_path):
        print(f"Error: Source directory does not exist: {src_path}")
        return False

    if is_junction_or_reparse(src_path):
        print(f"Notice: Directory is already an NTFS Junction link. No migration needed.")
        return False

    has_vhdx, vhdx_p = has_denied_descendant(src_path)
    if has_vhdx:
        print(f"Safety Guard: Detected virtual disk container ({vhdx_p}). Relocation forbidden.")
        return False

    # Automatically select partition with largest free space if not provided
    if not dst_root:
        target_drive = get_largest_free_drive(exclude_drives=["C"])
        if not target_drive:
            print("Error: No secondary non-system partition available for relocation.")
            return False
        dst_root = f"{target_drive}:\\AppData_Relocated"

    folder_name = os.path.basename(src_path)
    parent_name = os.path.basename(os.path.dirname(src_path))
    target_dir = os.path.join(dst_root, parent_name, folder_name)

    print("=" * 70)
    print(f"【AppData Seamless Relocation: {folder_name}】")
    print(f"  Source (C Drive): {src_path}")
    print(f"  Target (Non-C):   {target_dir}")
    sz = get_dir_size(src_path)
    print(f"  Estimated Gain:   {format_size(sz)}")
    print("=" * 70)

    with DiskReconciliation(f"Relocate: {folder_name}", "C"):
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        if os.path.exists(target_dir):
            print(f"Error: Target directory already exists: {target_dir}")
            return False

        print("  1/2 Moving directory contents (handling read-only locks with Robocopy)...")
        # Use robocopy to handle read-only attributes (e.g. .git objects) smoothly
        rc_cmd = [
            "robocopy",
            src_path,
            target_dir,
            "/E",
            "/MOVE",
            "/R:1",
            "/W:1"
        ]
        run_cmd(rc_cmd)

        # Remove leftover root folder if emptied
        if os.path.exists(src_path):
            try:
                shutil.rmtree(src_path)
            except Exception:
                # Force delete in powershell
                run_cmd(["powershell", "-NoProfile", "-Command", f"Remove-Item -Path '{src_path}' -Recurse -Force -ErrorAction SilentlyContinue"])

        if os.path.exists(src_path):
            print("Error: Could not completely remove source directory. Rolling back...")
            run_cmd(["robocopy", target_dir, src_path, "/E", "/MOVE", "/R:1", "/W:1"])
            return False

        print("  2/2 Creating native NTFS Junction...")
        out, err, code = run_cmd(["cmd", "/c", "mklink", "/J", src_path, target_dir])
        if code != 0:
            print(f"Failed to create Junction: {err}. Rolling back...")
            run_cmd(["robocopy", target_dir, src_path, "/E", "/MOVE", "/R:1", "/W:1"])
            return False

        print(f"Successfully relocated! Junction established: {out}")
    return True
