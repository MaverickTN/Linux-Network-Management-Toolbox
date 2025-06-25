import time

_cache = {}
TTL = 3600

def cache_role(username, role_data):
    _cache[username] = (role_data, time.time())

def get_cached_role(username):
    data = _cache.get(username)
    if not data:
        return None
    role, ts = data
    if time.time() - ts > TTL:
        del _cache[username]
        return None
    return role
