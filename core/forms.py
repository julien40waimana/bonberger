from django import forms
from .models import Utilisateur

class InscriptionPersonnelForm(forms.ModelForm):
    password = forms.CharField(
    widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}), 
    label="Mot de passe")

    class Meta:
        model = Utilisateur
        fields = ['last_name', 'first_name', 'email', 'photo_profil', 'password']