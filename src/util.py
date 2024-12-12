from pyramid.threadlocal import get_current_request

def get_root_request():
    """
    Retrieves the current Pyramid Request object using thread-local storage.
    
    Returns:
        pyramid.request.Request or None: The current request object if available, else None.
    """
    return get_current_request()
