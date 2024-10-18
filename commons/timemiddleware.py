import logging
import time

logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Request to {request.path} took {duration:.4f} seconds.")
        return response
