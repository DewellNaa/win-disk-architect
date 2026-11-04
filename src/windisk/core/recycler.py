import os
import shutil
import datetime
import json
from ..utils.system import format_size, get_dir_size, run_cmd

class DiskReconciliation:
    """Context manager for byte-level physical disk space reconciliation."""
    def __init__(self, task_name, drive_letter="C"):
        self.task_name = task_name
        self.drive = drive_letter.upper().replace(":", "").replace("\\", "")
        self.before_bytes = 0
        self.after_bytes = 0
        self.start_time = None

    def __enter__(self):
        try:
            usage = shutil.disk_usage(f"{self.drive}:\\")
            self.before_bytes = usage.free
        except Exception:
            self.before_bytes = 0
        self.start_time = datetime.datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            usage = shutil.disk_usage(f"{self.drive}:\\")
            self.after_bytes = usage.free
        except Exception:
            self.after_bytes = 0

        diff_bytes = self.after_bytes - self.before_bytes
        elapsed = (datetime.datetime.now() - self.start_time).total_seconds()

        print("\n" + "=" * 70)
        print(f"【Space Reconciliation: {self.task_name}】")
        print("=" * 70)
        print(f"  Drive: {self.drive}:")
        print(f"  Available Before: {format_size(self.before_bytes)}")
        print(f"  Available After:  {format_size(self.after_bytes)}")
        if diff_bytes > 0:
            print(f"  Net Released:     +{format_size(diff_bytes)} ⬆️ (Physical Free Sectors Increased)")
        elif diff_bytes == 0:
            print(f"  Net Released:     0 bytes (Locked or temporarily held)")
        else:
            print(f"  Notice: Available space changed by {format_size(abs(diff_bytes))} ⬇️")
        print(f"  Duration:         {elapsed:.2f}s")
        print("=" * 70 + "\n")

def safe_recycle(target_path, reason="User Cleanup"):
    """Move file or directory safely to the native Windows Recycle Bin with a recovery memo."""
    target_path = os.path.abspath(target_path)
    if not os.path.exists(target_path):
        print(f"Error: Target path does not exist: {target_path}")
        return False

    is_dir = os.path.isdir(target_path)
    sz = get_dir_size(target_path) if is_dir else os.path.getsize(target_path)
    parent_dir = os.path.dirname(target_path)

    print("Safely moving to Windows Recycle Bin:")
    print(f"  Target: {target_path}")
    print(f"  Size:   {format_size(sz)}")
    print(f"  Reason: {reason}")

    ps_type = "DeleteDirectory" if is_dir else "DeleteFile"
    ps_cmd = f'''
    Add-Type -AssemblyName Microsoft.VisualBasic;
    [Microsoft.VisualBasic.FileIO.FileSystem]::{ps_type}("{target_path}", "OnlyErrorDialogs", "SendToRecycleBin");
    '''
    out, err, code = run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd])
    if code != 0:
        print(f"Failed to move to Recycle Bin: {err}")
        return False

    today_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    memo_file = os.path.join(parent_dir, f"_RECOVERY_MEMO_{today_str}.txt")
    try:
        with open(memo_file, "w", encoding="utf-8") as f:
            f.write("=== WinDiskArchitect Safety & Recovery Memo ===\n")
            f.write(f"Deleted Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Original Target: {target_path}\n")
            f.write(f"Target Type: {'Directory' if is_dir else 'File'}\n")
            f.write(f"Released Size: {format_size(sz)}\n")
            f.write(f"Reason: {reason}\n")
            f.write("\n【How to Restore This Target?】\n")
            f.write("1. Open Windows Desktop 'Recycle Bin';\n")
            f.write(f"2. Locate '{os.path.basename(target_path)}';\n")
            f.write("3. Right-click and choose 'Restore'. It will return to its original location.\n")
        print(f"Recovery memo created: {os.path.basename(memo_file)}")
    except Exception:
        pass

    print("Successfully moved to Recycle Bin! You can restore it anytime.")
    return True
