# AI Guardian Remediation - Overview & Guide

`ai-guardian-remediation` is an automated service designed to fix security vulnerabilities in your source code. It uses AI agents (like Claude) to analyze security findings and automatically generate code fixes (Pull Requests).

## What does it do? (The "Inside" Story)

The project acts as a bridge between security scanners (like Semgrep or CVE detectors) and your code repository. Here is the high-level workflow for هر remediation:

1.  **Trigger**: It receives a request via API containing details about a vulnerability (CVE ID or SAST rule).
2.  **Clone**: It clones the target repository locally into a temporary directory.
3.  **Agent Logic**: It hands over the context to an AI Agent (Claude Code).
    - For **CVEs**, the agent looks at the vulnerable package and tries to patch it or upgrade it.
    - For **SAST findings**, the agent looks at the specific file and line number to suggest a code change that fixes the security flaw.
4.  **Verification**: It calculates the "diff" of the changes made by the AI.
5.  **Pull Request**: If a fix is generated, it creates a new branch, commits the changes, and opens a Pull Request on your Git provider (GitHub/GitLab) for human review.

## Main Components

- **API Layer**: FastAPI endpoints that receive remediation requests.
- **Service Layer**: Logic to manage the lifecycle (cloning, agent interaction, PR creation).
- **Core Agents**: The "brain" that uses AI to understand the code and the vulnerability.
- **Scheduler**: Background tasks that clean up temporary cloned repositories every few hours.

---

## Prerequisites

1.  **Node.js & npm**: Required to install the AI agent.
2.  **Claude Code CLI**: The engine that generates fixes.
3.  **Python 3.11+**: For the API layer.
4.  **uv**: For Python dependency management.
5.  **Git**: For code operations.

## Step 1: Install & Setup

### 1. Install & Authenticate Claude Code
If you see a permission error (`EACCES`), use `sudo`:
```bash
sudo npm install -g @anthropic-ai/claude-code
```

**CRITICAL**: You must log in to the Claude CLI once before running the project:
```bash
claude
```
*Follow the instructions in your browser to log in with your Anthropic account.*

### 2. Setup Project
```bash
cd /home/admins/workspace/ai-guardian-remediation
uv sync
```

## Step 2: Run Application
```bash
make run
```