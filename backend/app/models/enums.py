from enum import Enum


class AllotmentStatus(str, Enum):
    ALLOTTED = "ALLOTTED"
    NOT_ALLOTTED = "NOT_ALLOTTED"
    NOT_APPLIED = "NOT_APPLIED"
    CHECK_FAILED = "CHECK_FAILED"
