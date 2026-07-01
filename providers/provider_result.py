from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderResult:
    """
    Structured result returned by data providers.
    """

    success: bool
    data: object = None
    message: str = ""
    source: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        data=None,
        message="Data retrieved.",
        source="",
        warnings=None,
        metadata=None,
    ):
        return cls(
            success=True,
            data=data,
            message=message,
            source=source,
            warnings=list(warnings or []),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def fail(
        cls,
        message,
        data=None,
        source="",
        warnings=None,
        metadata=None,
    ):
        return cls(
            success=False,
            data=data,
            message=message,
            source=source,
            warnings=list(warnings or []),
            metadata=dict(metadata or {}),
        )
