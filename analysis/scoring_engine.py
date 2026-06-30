"""
Plugin-style scoring engine.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from config.logging_config import logger
from analysis.base_score import BaseScore
from analysis.score_result import ScoreResult


class ScoringEngine:
    """
    Discovers, registers, and executes score providers.
    """

    def __init__(self, providers=None):

        if providers is None:
            providers = self.discover_providers()

        self.providers = []

        for provider in providers:
            self.register(provider)

    @staticmethod
    def discover_providers(package_name="analysis"):
        """
        Discover BaseScore subclasses inside the analysis package.
        """

        package = importlib.import_module(package_name)
        providers = []
        seen = set()

        for module_info in pkgutil.walk_packages(
            package.__path__,
            f"{package.__name__}.",
        ):
            module = importlib.import_module(module_info.name)

            for _, candidate in inspect.getmembers(module, inspect.isclass):

                if candidate is BaseScore:
                    continue

                if not issubclass(candidate, BaseScore):
                    continue

                if inspect.isabstract(candidate):
                    continue

                if candidate in seen:
                    continue

                try:
                    providers.append(candidate())
                    seen.add(candidate)
                except Exception:
                    logger.exception(
                        "Failed to initialize score provider %s",
                        candidate.__name__,
                    )

        providers.sort(
            key=lambda provider: (
                provider.__class__.__module__,
                provider.__class__.__name__,
            )
        )

        return providers

    def register(self, provider):
        """
        Register one score provider instance.
        """

        if not isinstance(provider, BaseScore):
            raise TypeError("Score provider must inherit from BaseScore")

        self.providers.append(provider)

    def execute(self, context):
        """
        Execute all registered score providers.
        """

        results = []

        for provider in self.providers:

            try:
                result = provider.calculate(context)
            except Exception as error:
                logger.exception(
                    "Score provider %s failed",
                    provider.name,
                )
                result = ScoreResult(
                    name=provider.name,
                    value=0.0,
                    error=str(error),
                )

            if not isinstance(result, ScoreResult):
                raise TypeError("Score provider must return ScoreResult")

            results.append(result)

        return results
