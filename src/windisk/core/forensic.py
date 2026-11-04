import os
import re
from ..utils.system import format_size, get_dir_size, run_cmd

def scan_system_components():
    """Deep forensic inspection of Windows system storage components."""
    print("=" * 70)
    print("【Windows System Forensic & Component Storage Report】")
    print("=" * 70)

    # 1. WinSxS
    winsxs_path = r"C:\Windows\WinSxS"
    print("\n--- 1. WinSxS Component Store ---")
    if os.path.exists(winsxs_path):
        sz = get_dir_size(winsxs_path, max_depth=1)
        print(f"  Path: {winsxs_path}")
        print(f"  Estimated Size: ~{format_size(sz)}")
        print("  Recommendation: If major update residues exist, run:")
        print("     Dism.exe /Online /Cleanup-Image /StartComponentCleanup")
    else:
        print("  WinSxS directory not accessible.")

    # 2. DriverStore
    print("\n--- 2. DriverStore (FileRepository) ---")
    driver_store_path = r"C:\Windows\System32\DriverStore\FileRepository"
    if os.path.exists(driver_store_path):
        sz = get_dir_size(driver_store_path, max_depth=1)
        print(f"  Path: {driver_store_path}")
        print(f"  Total Size: ~{format_size(sz)}")

        out, _, code = run_cmd(["pnputil", "/enum-drivers"])
        if code == 0:
            oem_count = len(re.findall(r"Published Name\s*:\s*oem\d+\.inf", out, re.IGNORECASE))
            print(f"  Registered Third-Party OEM Drivers: {oem_count}")
            if sz < 1.5 * 1024 * 1024 * 1024:
                print("  🛡️ Safety Guard: Repository size is < 1.5 GB. Most content consists of active hardware drivers (Display, WiFi, Audio). DO NOT CLEAN.")
            else:
                print("  Notice: Large repository detected (>1.5 GB). Consider DriverStoreExplorer (RAPR) to remove obsolete graphics driver versions.")
    else:
        print("  DriverStore repository not accessible.")

    # 3. Windows Update Download Cache
    print("\n--- 3. Windows Update Download Cache ---")
    soft_dist = r"C:\Windows\SoftwareDistribution\Download"
    if os.path.exists(soft_dist):
        sz = get_dir_size(soft_dist)
        print(f"  Path: {soft_dist}")
        print(f"  Size: {format_size(sz)}")
    else:
        print("  SoftwareDistribution\\Download not found.")

    # 4. Crash Dumps
    print("\n--- 4. Crash Dumps & Diagnostic Logs ---")
    dump_files = [
        ("Full Memory Dump", r"C:\Windows\MEMORY.DMP"),
        ("Minidump Directory", r"C:\Windows\Minidump"),
        ("LiveKernelReports", r"C:\Windows\LiveKernelReports"),
    ]
    for label, dpath in dump_files:
        if os.path.exists(dpath):
            sz = get_dir_size(dpath) if os.path.isdir(dpath) else os.path.getsize(dpath)
            if sz > 1024 * 1024:
                print(f"  [Present] {label:<22} Size: {format_size(sz):<10} Path: {dpath}")
        else:
            print(f"  [Absent]  {label:<22}")
