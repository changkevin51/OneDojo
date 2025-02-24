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