import os
import re
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

from ai_guardian_remediation.config import settings
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
        rule: str,
        rule_message: str,
        scm_secret: str,
    ):
        self.clone_path = clone_path
        self.repo_url = repo_url
        self.branch = branch
        self.file_path = self._process_file_path(file_path)
        self.line_number = line_number
        self.rule = rule
        self.rule_message = rule_message
        self.scm_secret = scm_secret

    # For the bug in SSD semgrep's SAST results, remove prefix matching /tools/scanResult/unzipped-<ID>/ from the file path
    def _process_file_path(self, file_path: str) -> str:
        file_path = os.path.normpath(file_path)

        pattern = r"^/tools/scanResult/unzipped-\d+/"
        file_path = re.sub(pattern, "", file_path)

        return file_path

    async def generate_fix(
        self, session_id: str = None, message_type: str = None, user_message: str = None
    ):
        message = user_message
        if message_type == "start_generate":
            message = GENERATE_FIX_PROMPT.format(
                line_number=self.line_number,
                file_path=self.file_path,
                rule=self.rule,
                rule_message=self.rule_message
            )
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=AGENT_SYSTEM_PROMPT,
                cwd=Path(self.clone_path),
                allowed_tools=["Read", "Write", "Bash", "WebSearch", "WebFetch"],
                permission_mode="acceptEdits",  # auto-accept file edits
                resume=session_id,
                model=settings.CLAUDE_CODE_MODEL,
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
        logging.info(
            f"Stream completed successfully - Processed {message_count} messages"
        )
