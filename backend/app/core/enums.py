"""
Shared enumerations used across the data model.
"""
from enum import Enum


class UserRole(str, Enum):
    student = "student"
    librarian = "librarian"


class CopyStatus(str, Enum):
    available = "available"
    on_loan = "on_loan"
    lost = "lost"
    withdrawn = "withdrawn"


class CopyCondition(str, Enum):
    new = "new"
    good = "good"
    fair = "fair"
    poor = "poor"
