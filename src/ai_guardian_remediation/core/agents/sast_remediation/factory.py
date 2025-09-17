_sast_remediators = {"claude_code": "ClaudeCodeSASTAgent"}


def import_sast_remediator(provider: str):
    sast_remediator_class = _sast_remediators[provider]
    module = __import__(
        f"ai_guardian_remediation.core.agents.sast_remediation.{provider}.agent",
        fromlist=[sast_remediator_class],
    )
    sast_remediator = getattr(module, sast_remediator_class)
    return sast_remediator


def get_sast_agent(
    provider: str,
    clone_path: str,
    repo_url: str,
    branch: str,
    file_path: str,
    line_number: int,
    rule_message: str,
    scm_secret: str,
):
    sast_remediator = import_sast_remediator(provider)
    return sast_remediator(
        clone_path=clone_path,
        repo_url=repo_url,
        branch=branch,
        file_path=file_path,
        line_number=line_number,
        rule_message=rule_message,
        scm_secret=scm_secret,
    )
