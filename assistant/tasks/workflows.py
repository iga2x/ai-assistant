from assistant.tasks.task_types import Plan, PlanStep

def create_passive_recon_plan(target: str) -> Plan:
    """Create a multi-step plan for passive reconnaissance."""
    return Plan(
        title=f"Passive Recon: {target}",
        intent="scan",
        risk_summary="Performs passive lookups (WHOIS, DNS) and simple HTTP requests. Low risk of detection.",
        steps=[
            PlanStep(
                description=f"Whois lookup for {target}",
                command=f"whois {target}",
                requires_approval=False
            ),
            PlanStep(
                description=f"DNS enumeration for {target}",
                command=f"dig {target} ANY",
                requires_approval=False
            ),
            PlanStep(
                description=f"Check robots.txt on {target}",
                command=f"curl -s http://{target}/robots.txt",
                requires_approval=True
            ),
            PlanStep(
                description=f"HTTP headers for {target}",
                command=f"curl -I http://{target}",
                requires_approval=False
            )
        ]
    )
