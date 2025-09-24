from abc import ABC, abstractmethod


class SASTRemediationAgent(ABC):
    @abstractmethod
    async def generate_fix(self, **kwargs):
        raise NotImplementedError()

    # @abstractmethod
    async def process_approval(self, **kwargs):
        raise NotImplementedError()
