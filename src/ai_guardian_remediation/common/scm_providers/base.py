from abc import ABC, abstractmethod


class SCMProvider(ABC):
    @abstractmethod
    def create_pull_request(self, **kwargs) -> str:
        pass


def get_git_provider(provider_type, repo_url, clone_path, token):
    if provider_type == "github":
        from ai_guardian_remediation.common.scm_providers.github import GithubProvider

        print("Giiihub")
        return GithubProvider(repo_url, clone_path, token)
    else:
        raise ValueError(f"Unsupported provider: {provider_type}")
