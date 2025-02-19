from rest_framework_simplejwt.tokens import RefreshToken



def generate_tokens_for_user(user, request=None):
    token = RefreshToken.for_user(user)
    return {"refresh": str(token), "access": str(token.access_token)}

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')