_cve_remediators = {"claude_code": "ClaudeCode"}


def import_cve_remediator(provider):
    cve_remediator_class = _cve_remediators[provider]
    module = __import__(
        f"core.agents.{provider}.agent", fromlist=[cve_remediator_class]
    )
    cve_remediator = getattr(module, cve_remediator_class)
    return cve_remediator


def get_cve_agent(provider: str):
    cve_remediator = import_cve_remediator(provider)
    return cve_remediator()
