try:
    import oso
except ImportError as e:
    raise RuntimeError("In order to use the `Oso` integration, install this package with the `oso` extra!") from e
