def to_dict(obj):

    if hasattr(obj, "model_dump"):

        return obj.model_dump()

    if hasattr(obj, "dict"):

        return obj.dict()

    if isinstance(obj, dict):

        return obj

    return {}