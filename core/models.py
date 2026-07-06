from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.db import models

class Utilisateur(AbstractUser):
    ROLES = (
        ('superadmin', 'Superadmin'),
        ('prefet', 'Préfet des Études'),
        ('dir_etudes', 'Directeur des Études'),
        ('dir_discipline', 'Directeur de Discipline'),
        ('secretaire', 'Secrétaire'),
        ('comptable', 'Comptable'),
        ('professeur', 'Professeur'),
        ('receptionniste', 'Réceptionniste'),
        ('eleve', 'Élève'),
    )
    role = models.CharField(max_length=20, choices=ROLES, default='eleve')
    matricule = models.CharField(max_length=50, unique=True, null=True, blank=True)
    photo_profil = models.ImageField(upload_to="profils/", default="profils/default.png", null=True, blank=True)

    def save(self, *args, **kwargs):
        # Si c'est un élève et qu'il n'a pas de mot de passe défini, on utilise son matricule
        if self.role == 'eleve' and self.matricule and not self.password:
            self.set_password(self.matricule)
        super().save(*args, **kwargs)

class NotificationPrefet(models.Model):
    message = models.TextField()
    cree_le = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    def __str__(self):
        return self.message

class CoursAttribue(models.Model):
    professeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, limit_choices_to={'role': 'professeur'})
    nom_cours = models.CharField(max_length=100)
    classe = models.CharField(max_length=50)
    heures_attribuees = models.IntegerField()
    heures_effectuees = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.nom_cours} - {self.professeur.last_name}"

class SituationEleve(models.Model):
    eleve = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, limit_choices_to={'role': 'eleve'})
    solde_financier = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bulletin_url = models.FileField(upload_to="bulletins/", null=True, blank=True)

Utilisateur = get_user_model()
class AnnonceEcole(models.Model):
    TYPES = (
        ('info', 'Information Générale'),
        ('vacances', 'Vacances / Congés'),
        ('ferie', 'Jour Férié'),
    )
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    type_annonce = models.CharField(max_length=20, choices=TYPES, default='info')
    cree_le = models.DateTimeField(auto_now_add=True)
    date_evenement = models.DateField(null=True, blank=True, help_text="Date optionnelle du début de l'événement")

    def __str__(self):
        return f"[{self.get_type_annonce_display()}] {self.titre}"


class SanctionEleve(models.Model):
    TYPES_SANCTION = (
        ('retard', 'Retardateur Récurent'),
        ('puni', 'Élève Puni (Consigne/Retenue)'),
        ('exclu', 'Élève Exclu Temporairement'),
    )
    eleve = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, limit_choices_to={'role': 'eleve'})
    type_sanction = models.CharField(max_length=20, choices=TYPES_SANCTION)
    motif = models.TextField()
    date_debut = models.DateField(auto_now_add=True)
    date_fin = models.DateField(null=True, blank=True, help_text="Laisser vide si permanent ou déjà réglé")
    actif = models.BooleanField(default=True, help_text="Décochez si la punition est levée")
class CoursAttribue(models.Model):
    professeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, limit_choices_to={'role': 'professeur'}, verbose_name="Enseignant")
    nom_cours = models.CharField(max_length=100, verbose_name="Nom du Cours")
    classe = models.CharField(max_length=50, verbose_name="Classe / Promotion")
    heures_attribuees = models.IntegerField(verbose_name="Volume horaire total attribué")
    heures_effectuees = models.IntegerField(default=0, verbose_name="Heures validées par le prof")

    def __str__(self):
        return f"{self.nom_cours} ({self.classe}) - Prof. {self.professeur.last_name}"

    @property
    def progression_pourcentage(self):
        if self.heures_attribuees > 0:
            return min(int((self.heures_effectuees / self.heures_attribuees) * 100), 100)
        return 0
    def __str__(self):
        return f"{self.eleve.first_name} {self.eleve.last_name} - {self.get_type_sanction_display()}"