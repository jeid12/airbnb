from django.http import HttpResponseForbidden
from functools import wraps

from django.shortcuts import render

def host_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            
            return  HttpResponseForbidden(render(request, '403_forbidden.html'))
        if getattr(user, 'role', None) != 'host':
            return HttpResponseForbidden(render(request, '403_forbidden.html'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view
