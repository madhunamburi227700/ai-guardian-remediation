from ai_guardian_remediation.core.agents.cve_remediation.base import CVERemediationAgent

import os
import logging

from pathlib import Path
from claude_code_sdk import (
    ClaudeSDKClient,
    ClaudeCodeOptions,
    AssistantMessage,
    SystemMessage,
    ResultMessage,
    TextBlock,
)

from ai_guardian_remediation.core.agents.cve_remediation.claude_code.prompts import (
    SOLUTIONIZE_PROMPT,
    APPLY_FIX_PROMPT,
)


# Implement the methods here
class ClaudeCode(CVERemediationAgent):
    def __init__(
        self,
        clone_path: str,
        repo_url: str,
        branch: str,
        scm_secret: str,
    ):
        self.clone_path = clone_path
        self.repo_url = repo_url
        self.branch = branch
        self.scm_secret = scm_secret  # Only Github for now

    @staticmethod
    def _init_query_solutionize(cve_id: str, package: str):
        return f"The vulnerability is {cve_id} that affects package {package}"

    async def solutionize(
        self,
        session: str = None,
        cve_id: str = None,
        package: str = None,
        message_type: str = None,
        input_message: str = None,
    ):
        message = input_message
        if message_type == "start_generate":
            message = self._init_query_solutionize(cve_id, package)
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=SOLUTIONIZE_PROMPT,
                cwd=Path(self.clone_path),
                allowed_tools=["Read", "Write", "Bash", "WebSearch", "WebFetch"],
                permission_mode="acceptEdits",  # auto-accept file edits
                resume=session,
            )
        ) as client:
            await client.query(message)
            async for data in self._receive_response(client=client):
                yield data

    @staticmethod
    def _init_query_apply_fix(cve_id: str, package: str):
        return f"The vulnerability {cve_id} affects package {package}. Please proceed with the git related work"

    async def apply_fix(
        self,
        session: str = None,
        cve_id: str = None,
        package: str = None,
        message_type: str = None,
        input_message: str = None,
    ):
        message = input_message
        if message_type == "start_apply":
            message = self._init_query_apply_fix(cve_id, package)
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=APPLY_FIX_PROMPT.format(repo_url=self.repo_url),
                cwd=Path(self.clone_path),  # Can be string or Path
                allowed_tools=[
                    "Read",
                    "Write",
                    "Bash",
                    "mcp__github__create_branch",
                    "mcp__github__create_or_update_file",
                    "mcp__github__create_pull_request",
                    "mcp__github__get_commit",
                    "mcp__github__get_file_contents",
                    "mcp__github__get_me",
                    "mcp__github__get_pull_request",
                    "mcp__github__list_branches",
                    "mcp__github__list_commits",
                    "mcp__github__list_pull_requests",
                ],
                permission_mode="acceptEdits",
                mcp_servers={
                    "github": {
                        "command": os.path.join(
                            os.getcwd(), "bin", "github-mcp-server"
                        ),
                        "args": ["stdio"],
                        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": self.scm_secret},
                    }
                },
                resume=session,
            )
        ) as client:
            await client.query(message)
            async for data in self._receive_response(client=client):
                yield data

    async def _receive_response(self, client: ClaudeSDKClient):
        message_count = 0
        async for message in client.receive_response():
            logging.info(message)
            message_count += 1

            if isinstance(message, AssistantMessage):
                logging.info(
                    f"Processing AssistantMessage {message_count} with {len(message.content)} blocks"
                )
                for block in message.content:
                    if isinstance(block, TextBlock):
                        data = {"type": "content", "content": block.text}
                        yield data

            elif isinstance(message, SystemMessage):
                logging.info(
                    f"Processing SystemMessage {message_count} - Subtype: {message.subtype}"
                )
                data = {
                    "type": "system",
                    "subtype": message.subtype,
                    "data": message.data,
                }
                yield data

            elif isinstance(message, ResultMessage):
                logging.info(
                    f"Query completed - Cost: ${message.total_cost_usd:.4f}, Duration: {message.duration_ms}ms, Turns: {message.num_turns}, Error: {message.is_error}"
                )
                data = {
                    "type": "result",
                    "cost_usd": message.total_cost_usd,
                    "duration_ms": message.duration_ms,
                    "num_turns": message.num_turns,
                    "session_id": message.session_id,
                    "is_error": message.is_error,
                }
                yield data

        logging.info(
            f"Stream completed successfully - Processed {message_count} messages"
        )
