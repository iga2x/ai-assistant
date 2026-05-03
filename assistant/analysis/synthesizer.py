"""
ResultSynthesizer — post-execution output interpreter.

Ownership: REPL calls this AFTER Executor returns ExecutionResult.
Execution never happens here.

Strategy:
1. Try deterministic parsing first (fast, no AI call)
2. Fall back to AI synthesis only when:
   - plan.needs_analysis is True
   - execution failed
   - output is complex / multi-step / long
   - simple parser found nothing useful
"""

import re
from typing import Optional, TYPE_CHECKING, List

if TYPE_CHECKING:
    from assistant.actions.executor import ExecutionResult
    from assistant.tasks.task_types import Plan


# ---------------------------------------------------------------------------
# Deterministic parsers — interpret command output without AI
# ---------------------------------------------------------------------------

def _parse_ip_addr(stdout: str) -> Optional[str]:
    """Extract primary non-loopback IPv4 from `ip addr show` output."""
    for line in stdout.splitlines():
        # Handle cases with extra text or specific formatting
        m = re.search(r'inet\s+((?!127\.)\d{1,3}(?:\.\d{1,3}){3})', line)
        if m:
            return m.group(1)
    return None


def _parse_default_gateway(stdout: str) -> Optional[str]:
    """Extract gateway IP from `ip route show default` or `ip route` output."""
    for line in stdout.splitlines():
        # Match 'default via X.X.X.X' or just 'via X.X.X.X' in a route line
        m = re.search(r'(?:default\s+)?via\s+([\d\.]+)', line)
        if m:
            return m.group(1)
    # Also handle `hostname -I` style
    tokens = stdout.strip().split()
    if tokens and re.match(r'^\d{1,3}(?:\.\d{1,3}){3}$', tokens[0]):
        return tokens[0]
    return None


def _parse_nmap_summary(stdout: str) -> Optional[str]:
    """Summarise nmap scan output."""
    if not stdout:
        return None
    open_ports = []
    for line in stdout.splitlines():
        # e.g. "22/tcp   open  ssh"
        m = re.match(r'(\d+/\w+)\s+open\s+(\S+)', line.strip())
        if m:
            open_ports.append(f"{m.group(1)} ({m.group(2)})")
    # Closed-port note - handle multiple formats:
    # "1000 closed tcp ports" or "All 1000 scanned ports on localhost are closed"
    closed_match = re.search(r'(\d+)\s+(?:closed|filtered)\s+(?:tcp|udp)\s+ports?', stdout, re.IGNORECASE)
    if not closed_match:
        closed_match = re.search(r'All\s+(\d+)\s+scanned\s+ports.*?\s+are\s+(?:closed|filtered)', stdout, re.IGNORECASE)
    if open_ports:
        summary = f"Open ports found: {', '.join(open_ports)}."
        if closed_match:
            summary += f" ({closed_match.group(1)} ports closed/filtered.)"
        return summary
    if closed_match:
        return f"No open ports. All {closed_match.group(1)} scanned ports are closed or filtered."
    # Generic fallback
    if "Host seems down" in stdout:
        return "Host appears to be down or not responding to probes."
    return None


def _parse_nmap_discovery(stdout: str) -> Optional[str]:
    """Parse nmap host discovery (nmap -sn) output."""
    if not stdout:
        return None

    hosts = []
    for line in stdout.splitlines():
        m = re.search(r'Nmap scan report for\s+([^\s\(\)]+)', line)
        if m:
            hosts.append(m.group(1))

    if hosts:
        # Filter out localhost if it's the only result
        if len(hosts) == 1 and hosts[0] in ["127.0.0.1", "localhost"]:
            return "No additional network devices found."
        # Remove duplicates while preserving order
        seen = set()
        unique_hosts = []
        for host in hosts:
            if host not in seen:
                seen.add(host)
                unique_hosts.append(host)
        return f"Discovered devices: {', '.join(unique_hosts)}"
    return None


def _parse_ss_tuln(stdout: str) -> Optional[str]:
    """Extract listening ports from `ss -tuln` output."""
    ports = set()
    for line in stdout.splitlines():
        # Extract port from e.g. "0.0.0.0:80" or "[::]:80" or "*:80"
        m = re.search(r'(?::|\*)(\d+)\s+', line)
        if m:
            port = m.group(1)
            if port not in ["53", "5353"]: # Skip common low-level system ports for brevity
                ports.add(port)
    if ports:
        return f"Listening ports: {', '.join(sorted(list(ports), key=int))}."
    return None


def _parse_hostname_i(stdout: str) -> Optional[str]:
    """Extract IP from `hostname -I` output."""
    tokens = stdout.strip().split()
    if tokens and re.match(r'^\d{1,3}(?:\.\d{1,3}){3}$', tokens[0]):
        return tokens[0]
    return None


# ---------------------------------------------------------------------------
# Heuristic: should we call AI for synthesis?
# ---------------------------------------------------------------------------

_COMPLEX_COMMANDS = frozenset([
    "nmap", "nuclei", "nikto", "sqlmap", "ffuf", "wfuzz",
    "gobuster", "dirb", "metasploit", "hashcat", "john",
    "hydra", "medusa", "netcat", "nc", "tcpdump", "wireshark",
])


def _needs_ai_synthesis(plan: "Plan", result: "ExecutionResult") -> bool:
    """Decide if an AI synthesis call is warranted."""
    if getattr(plan, 'needs_analysis', False):
        return True
    if result.failed_steps:
        return True
    if len(result.steps) > 2:
        return True
    # Check if any step ran a complex tool
    for step in result.steps:
        cmd = step.command.lower()
        if any(tool in cmd for tool in _COMPLEX_COMMANDS):
            return True
    # Long combined output
    if len(result.combined_output) > 1500:
        return True
    return False


# ---------------------------------------------------------------------------
# Main synthesis function
# ---------------------------------------------------------------------------

async def synthesize_result(
    plan: "Plan",
    result: "ExecutionResult",
    ai_router=None,
) -> Optional[str]:
    """
    Return a human-readable summary of execution results.
    Never calls AI for simple/trivial output.
    Returns None if nothing useful to say (caller skips printing).
    """
    if not result or not result.steps:
        return None

    # -----------------------------------------------------------------------
    # 1. Failure synthesis (deterministic — always show, brief AI if useful)
    # -----------------------------------------------------------------------
    if result.failed_steps:
        # If there's an AI router and it's a complex failure, let AI explain
        if ai_router:
             prompt = (
                 f"The user tried to: '{plan.title}'.\n"
                 f"The command failed. Output:\n{result.combined_output[:1000]}\n\n"
                 "Explain why it failed in one short sentence and suggest a fix if obvious."
             )
             try:
                 import json as _json
                 raw = await ai_router.chat_completion([{"role": "user", "content": prompt}], json_mode=False)
                 return raw.strip()
             except:
                 pass
        
        # Fallback to deterministic failure msg
        failed_cmds = [s.command for s in result.steps if s.status == "failed"]
        stderr_snippets = [s.stderr[:200] for s in result.steps if s.status == "failed" and s.stderr]
        msg = f"Step failed: `{failed_cmds[0] if failed_cmds else 'unknown'}`."
        if stderr_snippets:
            msg += f"\nError: {stderr_snippets[0].strip()}"
        return msg

    # -----------------------------------------------------------------------
    # 2. Deterministic extraction (combine all steps)
    # -----------------------------------------------------------------------
    parts = []
    for step in result.steps:
        cmd = step.command.lower()
        out = step.stdout
        
        if "ip addr" in cmd or "ifconfig" in cmd:
            ip = _parse_ip_addr(out)
            if ip: parts.append(f"Local IP: **{ip}**")
            
        if "ip route" in cmd or "route" in cmd:
            gw = _parse_default_gateway(out)
            if gw: parts.append(f"Default gateway: **{gw}**")
            
        if "nmap" in cmd:
            # Try port scan parsing first
            s = _parse_nmap_summary(out)
            if s: parts.append(s)
            # Also try host discovery parsing
            d = _parse_nmap_discovery(out)
            if d: parts.append(d)
            
        if "hostname" in cmd:
            ip = _parse_hostname_i(out)
            if ip: parts.append(f"IP: **{ip}**")
            
        if "ss -tuln" in cmd or "netstat -tuln" in cmd:
            ps = _parse_ss_tuln(out)
            if ps: parts.append(ps)

    if parts:
        # De-duplicate parts while preserving order
        unique_parts = []
        for p in parts:
            if p not in unique_parts:
                unique_parts.append(p)
        return "  ".join(unique_parts)

    # -----------------------------------------------------------------------
    # 3. AI synthesis — only for complex/flagged plans
    # -----------------------------------------------------------------------
    if ai_router and _needs_ai_synthesis(plan, result):
        import json as _json
        prompt = (
            f"The user ran: '{plan.title}'.\n"
            f"Commands executed:\n"
            + "\n".join(
                f"  $ {s.command}\n  Output: {s.stdout[:600] if s.stdout else '(empty)'}"
                for s in result.steps
            )
            + "\n\nProvide a concise 1-3 sentence human-readable summary of what was found. "
              "Do not invent data. If nothing notable, say the command completed successfully."
        )
        try:
            raw = await ai_router.chat_completion(
                [{"role": "user", "content": prompt}],
                json_mode=False,
            )
            # Strip JSON wrapper if model returned one anyway
            if raw.strip().startswith("{"):
                try:
                    d = _json.loads(raw)
                    raw = d.get("content", raw)
                except Exception:
                    pass
            return raw.strip() if raw.strip() else None
        except Exception:
            return None

    return None
