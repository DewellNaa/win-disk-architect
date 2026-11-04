import os
import shutil
from ..utils.system import format_size, run_cmd, get_fixed_drives

def get_drive_status():
    """Get logical drive capacity and usage status."""
    ps_cmd = (
        "Get-PSDrive -PSProvider FileSystem | Select-Object Root, "
        "@{N='UsedGB';E={[math]::Round($_.Used/1GB,2)}}, "
        "@{N='FreeGB';E={[math]::Round($_.Free/1GB,2)}}, "
        "@{N='FreeRatio';E={[math]::Round(($_.Free/($_.Used+$_.Free))*100,1)}} | "
        "ConvertTo-Json"
    )
    out, _, code = run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd])
    return out

def get_system_reserved_files():
    """Check existence and size of core Windows system reserved files."""
    drives = get_fixed_drives()
    targets = ["hiberfil.sys", "pagefile.sys", "swapfile.sys"]
    results = []

    for d in drives:
        for t in targets:
            full_p = f"{d}:\\{t}"
            if os.path.exists(full_p):
                try:
                    sz = os.path.getsize(full_p)
                    results.append({"path": full_p, "size_bytes": sz, "size_str": format_size(sz), "status": "present"})
                except Exception:
                    results.append({"path": full_p, "size_bytes": None, "size_str": "Locked", "status": "locked"})
            else:
                results.append({"path": full_p, "size_bytes": 0, "size_str": "0 KB", "status": "absent"})
    return results

def get_partition_topology():
    """Inspect physical disk and partition structure."""
    ps_cmd = (
        "Get-Partition | Select-Object DiskNumber, PartitionNumber, DriveLetter, "
        "@{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}, Type | Format-Table -AutoSize | Out-String"
    )
    out, _, _ = run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd])
    return out
