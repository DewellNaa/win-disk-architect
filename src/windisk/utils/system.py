import os
import sys
import subprocess
import ctypes
import shutil

# Windows File Attributes Flags
FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000

SYSTEM_EXCLUDED_DIRS = {
    "$recycle.bin",
    "system volume information",
    "recovery",
    "msocache",
    "config.msi",
    "windows",
    "$windows.~bt",
    "perflogs"
}

SKIP_DIR_NAMES = {
    "node_modules",
    ".git",
    ".svn",
    ".hg",
    ".vscode",
    ".idea"
}

def is_admin():
    """Check if the current process has administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def format_size(bytes_val):
    """Format bytes into human-readable string (KB, MB, GB, TB)."""
    if bytes_val is None or bytes_val < 0:
        return "Unknown"
    tb = bytes_val / (1024 ** 4)
    gb = bytes_val / (1024 ** 3)
    mb = bytes_val / (1024 ** 2)
    kb = bytes_val / 1024
    if tb >= 1.0:
        return f"{tb:6.2f} TB"
    elif gb >= 1.0:
        return f"{gb:6.2f} GB"
    elif mb >= 1.0:
        return f"{mb:6.1f} MB"
    else:
        return f"{kb:6.1f} KB"

def get_dir_size(path, max_depth=None, current_depth=0):
    """Recursively calculate the total size of a directory, skipping junctions and offline files."""
    total = 0
    if not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except Exception:
            return 0
    if max_depth is not None and current_depth > max_depth:
        return 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if is_junction_or_reparse(entry) or is_offline_cloud_file(entry):
                        continue
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += get_dir_size(entry.path, max_depth, current_depth + 1)
                except Exception:
                    pass
    except Exception:
        pass
    return total

def run_cmd(cmd_list):
    """Run an external command and safely capture output."""
    try:
        proc = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except Exception as e:
        return "", str(e), -1

def is_junction_or_reparse(entry_or_path):
    """Determine if a directory entry or path is an NTFS junction or reparse point."""
    try:
        if hasattr(entry_or_path, 'is_symlink'):
            if entry_or_path.is_symlink():
                return True
            st = entry_or_path.stat(follow_symlinks=False)
            attrs = getattr(st, 'st_file_attributes', 0)
            return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
        else:
            p = str(entry_or_path)
            if os.path.islink(p):
                return True
            st = os.lstat(p)
            attrs = getattr(st, 'st_file_attributes', 0)
            return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return True

def is_offline_cloud_file(entry):
    """Detect if file is stored exclusively on cloud (OneDrive / iCloud placeholder)."""
    try:
        st = entry.stat(follow_symlinks=False)
        attrs = getattr(st, 'st_file_attributes', 0)
        return bool(attrs & (FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS))
    except Exception:
        return False

def get_fixed_drives():
    """Return all fixed local drive letters (e.g. ['C', 'D'])."""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in range(65, 91):
        if bitmask & (1 << (letter - 65)):
            drv = f"{chr(letter)}:\\"
            dtype = ctypes.windll.kernel32.GetDriveTypeW(drv)
            if dtype == 3:  # DRIVE_FIXED
                drives.append(chr(letter))
    return drives

def get_largest_free_drive(exclude_drives=None):
    """Find the non-system drive with the largest available free space."""
    if exclude_drives is None:
        exclude_drives = ["C"]
    exclude_set = {d.upper() for d in exclude_drives}

    fixed = get_fixed_drives()
    candidates = []
    for d in fixed:
        if d.upper() in exclude_set:
            continue
        try:
            usage = shutil.disk_usage(f"{d}:\\")
            candidates.append((d, usage.free))
        except Exception:
            pass

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]

def has_denied_descendant(root_path, max_depth=2):
    """Protect against moving or deleting directories containing virtual hard disks (.vhdx/.vmdk)."""
    forbidden_exts = {".vhdx", ".vdi", ".vmdk"}
    try:
        for current_root, dirs, files in os.walk(root_path):
            rel_depth = current_root[len(root_path):].count(os.sep)
            if rel_depth > max_depth:
                dirs.clear()
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in forbidden_exts:
                    return True, os.path.join(current_root, f)
    except Exception:
        pass
    return False, ""
