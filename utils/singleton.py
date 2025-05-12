import abc
from typing import Any


class Singleton(abc.ABCMeta, type):
    _instances = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Call method for the singleton metaclass"""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class AbstractSingleton(abc.ABC, metaclass=Singleton):
    """Abstract singleton class for ensuring only one instance of a class"""

    pass
