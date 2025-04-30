from django.http import JsonResponse

class APIErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.path.startswith('/api/'):
            if response.status_code >= 500:
                return JsonResponse({
                    'error': 'Internal server error occurred'
                }, status=500)
                
        return response
    

from django.utils.deprecation import MiddlewareMixin
from .models import Dojo

class DojoContextMiddleware(MiddlewareMixin):
    """Middleware to add selected dojo information to request"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Get selected dojo from session
            selected_dojo_id = request.session.get('selected_dojo_id')
            
            # If no selected dojo but user has an assigned dojo, use that
            if not selected_dojo_id and hasattr(request.user, 'dojo') and request.user.dojo:
                selected_dojo_id = request.user.dojo.id
                request.session['selected_dojo_id'] = selected_dojo_id
                request.session['selected_dojo_name'] = request.user.dojo.name
            
            # Add dojo info to request for easy access in views
            if selected_dojo_id:
                try:
                    from .models import Dojo
                    dojo = Dojo.objects.get(id=selected_dojo_id)
                    request.selected_dojo = dojo
                except Dojo.DoesNotExist:
                    request.selected_dojo = None
            else:
                request.selected_dojo = None
                
        return None