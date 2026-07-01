import pytest

from providers.base_provider import BaseProvider


def test_base_provider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseProvider()


def test_partial_provider_cannot_be_instantiated():
    class PartialProvider(BaseProvider):
        def get_price_history(self, ticker, start=None, end=None):
            return None

    with pytest.raises(TypeError):
        PartialProvider()
