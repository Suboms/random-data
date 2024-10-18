from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.throttling import SimpleRateThrottle


class AnonUserRateThrottle(SimpleRateThrottle):
    scope = "anon"
    rate = "50/min"  # Ensure this is correctly set.
    max_data_range = 50

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None  # Only throttle unauthenticated requests.

        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }

    def throttle_failure(self):
        """
        Custom response when the request is throttled.
        """
        raise Throttled(
            detail={
                "detail": "Request limit exceeded. Please try again later.",
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "retry_after": self.wait(),  # Optionally include retry time in seconds
            }
        )


class FreeUserRateThrottle(SimpleRateThrottle):
    scope = "free"
    rate = "500/min"
    max_data_range = 1000

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {"scope": self.scope, "ident": ident}

class PaidUserRateThrottle(FreeUserRateThrottle):
    scope = 'paid'
    rate = '2000/min'
    max_data_range = 10000