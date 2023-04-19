try:
    import oso
except ImportError as e:
    raise RuntimeError("In order to use the `Oso` integration, install this package with the `oso` extra!") from e


from .sqlalchemy_oso.auth import authorize_model, register_models, default_polar_model_name
