from __future__ import annotations

from typing import Callable, TypeVar

RT = TypeVar("RT")


class UnauthorizedError(RuntimeError):
    """We raise this exception when a user tries to access a resource without the proper permissions."""

    def __init__(self, function: Callable[..., RT], *args: str, **kwargs: int):
        super().__init__("unauthorized access to resource")
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return (
            f"UnauthorizedError from [{self.function}] - ({self.args} ; {self.kwargs})"
        )
