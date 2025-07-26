from django.http import HttpResponseForbidden
from functools import wraps

def host_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            # Redirect to login or deny
            return HttpResponseForbidden("You must be logged in as a host to access this.")
        if getattr(user, 'role', None) != 'host':
            return HttpResponseForbidden("You do not have permission to perform this action.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
