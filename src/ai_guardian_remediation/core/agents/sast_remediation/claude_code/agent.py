from pathlib import Path
from claude_code_sdk import (
    query,
    ClaudeCodeOptions,
    AssistantMessage,
    SystemMessage,
    ResultMessage,
    TextBlock,
)
from ai_guardian_remediation.core.agents.sast_remediation.base import (
    SASTRemediationAgent,
)
from ai_guardian_remediation.core.agents.sast_remediation.claude_code.prompts import (
    AGENT_SYSTEM_PROMPT,
    GENERATE_FIX_PROMPT,
)


class ClaudeCodeSASTAgent(SASTRemediationAgent):
    def __init__(
        self,
        clone_path: str,
        repo_url: str,
        branch: str,
        file_path: str,
        line_number: int,
        rule_message: str,
        scm_secret: str,
    ):
        self.clone_path = clone_path
        self.repo_url = repo_url
        self.branch = branch
        self.file_path = file_path
        self.line_number = line_number
        self.rule_message = rule_message
        self.scm_secret = scm_secret

    async def generate_fix(self):
        prompt = GENERATE_FIX_PROMPT.format(
            line_number=self.line_number,
            file_path=self.file_path,
            rule_message=self.rule_message,
            repo_url=self.repo_url,
        )

        options = ClaudeCodeOptions(
            system_prompt=AGENT_SYSTEM_PROMPT,
            cwd=Path(self.clone_path),
            allowed_tools=["Read", "Write", "Bash"],
            permission_mode="acceptEdits",
        )

        async for data in self._run(prompt=prompt, options=options):
            yield data

    # async def process_approval(self):
    #     prompt = PROCESS_APPROVAL_PROMPT.format(
    #         line_number=self.line_number,
    #         file_path=self.file_path,
    #         rule_message=self.rule_message,
    #         repo_url=self.repo_url,
    #         branch=self.branch,
    #     )

    #     options = ClaudeCodeOptions(
    #         system_prompt=AGENT_SYSTEM_PROMPT,
    #         cwd=Path(self.clone_path),
    #         allowed_tools=[
    #             "Read",
    #             "Write",
    #             "Bash",
    #             "mcp__github__create_branch",
    #             "mcp__github__create_or_update_file",
    #             "mcp__github__create_pull_request",
    #             "mcp__github__get_commit",
    #             "mcp__github__get_file_contents",
    #             "mcp__github__get_me",
    #             "mcp__github__get_pull_request",
    #             "mcp__github__list_branches",
    #             "mcp__github__list_commits",
    #             "mcp__github__list_pull_requests",
    #         ],
    #         permission_mode="acceptEdits",
    #         mcp_servers={
    #             "github": {
    #                 "command": os.path.join(os.getcwd(), "bin", "github-mcp-server"),
    #                 "args": ["stdio"],
    #                 "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": self.scm_secret},
    #             }
    #         },
    #     )

    #     async for data in self._run(prompt=prompt, options=options):
    #         yield data

    async def _run(self, prompt: str, options: ClaudeCodeOptions):
        message_count = 0
        async for message in query(prompt=prompt, options=options):
            message_count += 1

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        yield {"type": "content", "content": block.text}

            elif isinstance(message, SystemMessage):
                yield {
                    "type": "system",
                    "subtype": message.subtype,
                    "data": message.data,
                }

            elif isinstance(message, ResultMessage):
                yield {
                    "type": "result",
                    "cost_usd": message.total_cost_usd,
                    "duration_ms": message.duration_ms,
                    "num_turns": message.num_turns,
                    "session_id": message.session_id,
                    "is_error": message.is_error,
                }

        print(f"Stream completed successfully - {message_count} messages processed.")
