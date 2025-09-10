from abc import ABC, abstractmethod


class CVERemediationAgent(ABC):
    @abstractmethod
    async def solutionize(self, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    async def apply_fix(self, **kwargs):
        raise NotImplementedError()
