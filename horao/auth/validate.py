from __future__ import annotations

from functools import wraps
from typing import Callable

from starlette.requests import Request

from horao.auth.error import UnauthorizedError
from horao.auth.permissions import RT, Namespace, Permission
from horao.auth.roles import User


def permission_required(
    namespace: Namespace, permission: Permission
) -> Callable[[Callable[..., RT]], Callable[..., RT]]:
    """
    Decorator to check if a user has the permission to access a resource.
    :param namespace: namespace to check
    :param permission: permission to check
    :return: function call if the user has the permission
    :raises: UnauthorizedError if the user does not have the permission
    """

    def decorator(func: Callable[..., RT]) -> Callable[..., RT]:
        @wraps(func)
        async def wrapper(*args: str, **kwargs: int) -> RT:
            for arg in args:
                if isinstance(arg, Request):
                    if not arg.user:
                        raise UnauthorizedError(func, *args, **kwargs)
                    if isinstance(arg.user, User):
                        if permission.Write and any(
                            [p for p in arg.user.permissions if p.can_write(namespace)]
                        ):
                            return await func(*args, **kwargs)
                        if permission.Read and any(
                            [p for p in arg.user.permissions if p.can_read(namespace)]
                        ):
                            return await func(*args, **kwargs)
            raise UnauthorizedError(func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator
