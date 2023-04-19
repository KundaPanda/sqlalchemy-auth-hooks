"""
This type stub file was generated by pyright.
"""

class DataFilter:
    """An object representing an abstract query over a particular data type"""
    def __init__(self, model, relations, conditions, types) -> None:
        ...
    
    @classmethod
    def parse(cls, polar, blob): # -> Self@DataFilter:
        ...
    


class Projection:
    """
    An object representing a named property (`field`) of a particular data type (`source`).
    `field` may be `None`, which user code must translate to a field (usually the primary key
    column in a database) that uniquely identifies the record.
    """
    def __init__(self, source, field) -> None:
        ...
    


class Relation:
    """An object representing a named relation between two data types"""
    def __init__(self, left, name, right) -> None:
        ...
    
    @classmethod
    def parse(cls, polar, left, name, right): # -> Self@Relation:
        ...
    


class Condition:
    """
    An object representing a WHERE condition on a query.

    `cmp` is an equality or inequality operator.

    `left` and `right` may be Projections or literal data.
    """
    def __init__(self, left, cmp, right) -> None:
        ...
    
    @classmethod
    def parse(cls, polar, left, cmp, right): # -> Self@Condition:
        ...
    
    @staticmethod
    def parse_side(polar, side): # -> Projection:
        ...
    


