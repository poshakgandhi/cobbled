class HeadToGetMiddleware:
    """
    Middleware that converts HEAD requests into GET requests for compatibility
    with iommi views, then strips the response body for valid HTTP HEAD responses.
    This fixes Hugging Face Spaces health probe checks (which issue HEAD /).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_head = (request.method == "HEAD")
        if is_head:
            request.method = "GET"
        response = self.get_response(request)
        if is_head:
            response.content = b""
        return response
