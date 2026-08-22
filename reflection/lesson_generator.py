from abc import ABC, abstractmethod


class BaseReflector(ABC):

    name:str


    @abstractmethod
    def evaluate(self,state):
        pass