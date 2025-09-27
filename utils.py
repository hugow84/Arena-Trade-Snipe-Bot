def get_key_from_value(dictionary, value):
    """Get dictionary key from value"""
    for key, val in dictionary.items():
        if val == value:
            return key
    return None