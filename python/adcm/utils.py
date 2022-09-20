def get_obj_type(obj_type: str) -> str:
    if obj_type == "cluster object":
        return "service"
    elif obj_type == "service component":
        return "component"
    elif obj_type == "host provider":
        return "provider"

    return obj_type


def str_remove_non_alnum(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum())
