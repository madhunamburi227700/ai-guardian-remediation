from ai_guardian_remediation.core.agents.cve_remediation.base import CVERemediationAgent

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

    async def _receive_response(self, client: ClaudeSDKClient):
        message_count = 0
        async for message in client.receive_response():
            logging.info(f"Received message: {message}\n")
            message_count += 1

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        data = {"type": "content", "content": block.text}
                        yield data

            elif isinstance(message, SystemMessage):
                data = {
                    "type": "system",
                    "subtype": message.subtype,
                    "data": message.data,
                }
                yield data

            elif isinstance(message, ResultMessage):
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
