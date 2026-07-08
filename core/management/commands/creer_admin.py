from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Crée un super-administrateur automatiquement sur Render"

    def handle(self, *args, **options):
        User = get_user_model()
        # Modifie ici tes identifiants de connexion pour ton site en ligne :
        username = 'admin'
        email = 'admin@email.com'
        password = 'TonMotDePasseSecurise'

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS("--- SUPERUSER CRÉÉ AVEC SUCCÈS ---"))
        else:
            self.stdout.write(self.style.WARNING("Le superuser existe déjà."))