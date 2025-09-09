"""
Defines the abstract base class for a G-code dialect.
"""
from abc import ABC, abstractmethod

class BaseDialect(ABC):
    def __init__(self):
        self.g_code_map = {}
        self.m_code_map = {}
