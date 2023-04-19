"""
This type stub file was generated by pyright.
"""

from typing import Tuple
from .expression import Expression
from .variable import Variable

class TypeConstraint(Expression):
    def __init__(self, left, type_name) -> None: ...

def dot_path(expr: Expression) -> Tuple[Variable, ...]:
    """Get the path components of a (potentially nested) dot lookup. The path
    is returned as a tuple. The empty tuple is returned if input is not a dot
    operation.

    _this => (_this,)
    _this.created_by => (_this, 'created_by',)
    _this.created_by.username => (_this, 'created_by', 'username')"""
    ...