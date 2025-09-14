# modulo/__init__.py
"""
Define o pacote 'modulo'. Mantém a API pública de alto nível.
"""

from .core_loop import main_loop  # opcional: facilitar import externamente

__all__ = ["main_loop"]