def strcmp(lhs, rhs):
    """An example of a proper constant-time string comparison function"""
    if len(lhs) != len(rhs):
        return False
    result = 0
    for (lchr, rchr) in zip(lhs, rhs):
        result |= (ord(lchr) ^ ord(rchr))
    return result == 0
