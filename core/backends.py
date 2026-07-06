from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        # Si le champ 'username' contient une adresse email, on cherche par email
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
            
        try:
            # On tente de récupérer l'utilisateur via son adresse email
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None
        else:
            # Si l'utilisateur existe, on vérifie la validité de son mot de passe
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None