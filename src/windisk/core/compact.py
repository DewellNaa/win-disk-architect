from ..utils.system import run_cmd

def query_compact_state():
    """Query current Windows CompactOS state."""
    out, err, code = run_cmd(["compact", "/compactos:query"])
    is_compact = False
    if "is in the compact state" in out.lower() or "处于压缩状态" in out:
        is_compact = True
    return is_compact, out

def set_compact_state(enable=True):
    """Enable or disable Windows CompactOS (requires administrator privileges)."""
    arg = "always" if enable else "never"
    out, err, code = run_cmd(["compact", f"/compactos:{arg}"])
    return code == 0, out or err
