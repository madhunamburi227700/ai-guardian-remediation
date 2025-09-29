AGENT_SYSTEM_PROMPT = "You are a coding assistant, focused on helping with code editing, offering guidance on various programming tasks, and assisting with interactions with version control systems"

GENERATE_FIX_PROMPT = """In line {line_number} of the file located at {file_path}, the Semgrep tool has identified an issue based on a rule match:
RULE MESSAGE: {rule_message}
This message describes the specific code pattern detected and may include mitigation guidance. The correctness and completeness of your fix depend on how well you adhere to this guidance.
Note: The line number provided may not always be accurate if the source code has changed since the scan was performed. You should search at or near the specified line number in {file_path} to locate the relevant code pattern, using the rule message as your guide.

YOUR TASK:
a) **Analyze the rule message carefully**
At or near line {line_number} of {file_path}, identify the exact code pattern that triggered the finding and understand the remediation guidance in the rule message.
    - If the rule message includes a recommended fix or mitigation, you must implement it exactly as described.
    - If no remediation is provided, use your own judgment to apply a safe, minimal fix that resolves the issue without introducing unrelated changes.

b) **Plan and apply a fix**
- Resolve only the issue described in the rule message.
- Ensure your fix is minimal, correct, and consistent with the existing codebase.
- Do not introduce stylistic, speculative, or unrelated changes.
- Do not introduce any unrelated modifications

**Important**
Your fix must be driven by the rule message. Strict adherence is required when remediation guidance is provided. Deviation from it may result in incorrect or non-compliant fixes.
"""


# PROCESS_APPROVAL_PROMPT = """A fix has been applied for the Semgrep rule {rule_message}, which was detected in the codebase at file {file_path} on or near line {line_number}.

# YOUR TASK:
# - **Do not modify any code.** Only perform the steps related to the PR process as outlined below:
# - Create a new Git branch reflecting the nature of the fix, and append a random alphanumeric suffix to the branch name to ensure uniqueness (e.g., fix/<brief-line-about-what-the-semgrep-rule-is-about>-123abc).
# - Commit the fix to this branch with a clear, concise commit message referencing the Semgrep rule.
# - Open a pull request to {repo_url} from the newly created branch, targeting the {branch} branch
# """
