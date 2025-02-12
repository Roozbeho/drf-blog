from rest_framework_simplejwt.tokens import RefreshToken



def generate_tokens_for_user(user, request=None):
    token = RefreshToken.for_user(user)
    return {"refresh": str(token), "access": str(token.access_token)}