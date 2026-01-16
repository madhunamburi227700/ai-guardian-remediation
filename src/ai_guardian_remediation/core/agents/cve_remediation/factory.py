_cve_remediators = {"claude_code": "ClaudeCode"}


def import_cve_remediator(provider):
    if provider not in _cve_remediators:
        raise ValueError(f"Unsupported CVE remediator provider: {provider}")

    cve_remediator_class = _cve_remediators[provider]
    module = __import__(
        f"ai_guardian_remediation.core.agents.cve_remediation.{provider}.agent",
        fromlist=[cve_remediator_class],
    )
    cve_remediator = getattr(module, cve_remediator_class)
    return cve_remediator


def get_cve_agent(
    provider: str, clone_path: str, repo_url: str, branch: str, scm_secret: str
):
    cve_remediator = import_cve_remediator(provider)
    return cve_remediator(
        clone_path=clone_path, repo_url=repo_url, branch=branch, scm_secret=scm_secret
    )
