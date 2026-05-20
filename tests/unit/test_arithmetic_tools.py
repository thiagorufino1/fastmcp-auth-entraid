from __future__ import annotations

import pytest

from app.tools.divisao import _divisao
from app.tools.multiplicacao import _multiplicacao
from app.tools.soma import _soma
from app.tools.subtracao import _subtracao


class TestArithmeticTools:
    def test_soma(self):
        assert _soma(2, 3) == {"a": 2, "b": 3, "resultado": 5}

    def test_subtracao(self):
        assert _subtracao(10, 4) == {"a": 10, "b": 4, "resultado": 6}

    def test_multiplicacao(self):
        assert _multiplicacao(6, 7) == {"a": 6, "b": 7, "resultado": 42}

    def test_divisao(self):
        assert _divisao(8, 2) == {"a": 8, "b": 2, "resultado": 4.0}

    def test_divisao_by_zero_raises(self):
        with pytest.raises(ValueError, match="divisor must be different from zero"):
            _divisao(8, 0)
