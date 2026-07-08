from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import NotificationPrefet, CoursAttribue, SituationEleve
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import AnnonceEcole, SanctionEleve, SituationEleve, Utilisateur
from django.db.models import Q
import random
from django.db.models import Sum
from .models import SituationEleve, Utilisateur
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from .models import Utilisateur,CoursAttribue,NoteEleve
from .forms import InscriptionPersonnelForm
from django.views.generic import CreateView, ListView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Count
from core.models import FraisScolaire, Paiement
import uuid

@login_required
def dashboard_aiguillage(request):
    role = request.user.role
    
    # 1. SI L'UTILISATEUR EST EN ATTENTE, ON LE PASSE AUTOMATIQUEMENT EN ÉLÈVE
    # 1. SI L'UTILISATEUR EST EN ATTENTE, ON LE PASSE AUTOMATIQUEMENT EN ÉLÈVE (Sauf si c'est le superadmin)
    if not request.user.is_superuser and (role == 'en_attente' or not role):
        request.user.role = 'eleve'
        request.user.save()
        role = 'eleve'

    # 2. LES REDIRECTIONS DIRECTES
    if request.user.is_superuser or role == 'superadmin':
        return redirect('/admin') # Te renvoie directement sur le vrai panneau d'administration de Django
    elif role == 'prefet':
        return redirect('dashboard_prefet')
    elif role == 'professeur':
        return redirect('dashboard_professeur')
    elif role == 'eleve':
        return redirect('dashboard_eleve')  # L'élève ira directement ici désormais !
    elif role == 'receptionniste':
        return redirect('dashboard_receptionniste')
    elif role == 'comptable':
        return redirect('dashboard_comptable')
        
    # Plus besoin du bloc 'en_attente' ici puisqu'il est traité plus haut
        
    elif role in ['discipline', 'Directeur de discipline', 'dir_discipline']:
        return render(request, 'core/dashboard_discipline.html')
    elif role in ['dir_etudes', 'Directeur des études', 'DIRECTEUR DES ÉTUDES']:
        return render(request, 'core/dashboard_dir_etudes.html')
    # Ajouter les autres redirections ici au fur et à mesure...
    else:
        return render(request, 'core/dashboard_generique.html')

@login_required
def dashboard_prefet(request):
    if request.user.role != 'prefet':
        return redirect('aiguillage')
    notifications = NotificationPrefet.objects.all().order_by('-cree_le')
    return render(request, 'core/dashboard_prefet.html', {'notifications': notifications})

@login_required
def dashboard_professeur(request):
    # Sécurité : s'assurer que c'est bien un professeur
    if request.user.role != 'professeur':
        return redirect('aiguillage')

    # 1. Récupérer toutes les attributions de cours du prof connecté
    cours = CoursAttribue.objects.filter(professeur=request.user)
    
    # Récupération des paramètres de filtrage pour les élèves (depuis la colonne gauche)
    attribution_id = request.GET.get('attribution')
    attribution_selectionnee = None
    eleves = []
    notes_existantes = {}

    if attribution_id:
        try:
            # On récupère le cours sélectionné s'il appartient bien à ce prof
            attribution_selectionnee = cours.get(id=attribution_id)
            # Filtrer les élèves inscrits dans l'établissement
            eleves = Utilisateur.objects.filter(role='eleve')
            
            # Récupérer les notes déjà saisies pour ce cours afin de les pré-remplir
            notes = NoteEleve.objects.filter(cours_attribue=attribution_selectionnee)
            notes_existantes = {note.eleve_id: note for note in notes}
        except CoursAttribue.DoesNotExist:
            pass

    # 2. Gestion des actions POST
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # --- ACTION EXISTANTE : Pointage des heures ---
        if action == "cocher_heure":
            cours_id = request.POST.get('cours_id')
            try:
                c = cours.get(id=cours_id)
                c.heures_effectuees += 1
                c.save()
                messages.success(request, f"Heure validée pour le cours de {c.nom_cours}.")
            except CoursAttribue.DoesNotExist:
                pass
            return redirect('dashboard_professeur')

        # --- NOUVELLE ACTION : Envoi et publication des notes ---
        elif action == "enregistrer_notes" and attribution_selectionnee:
            for eleve in eleves:
                interro_val = request.POST.get(f'interro_{eleve.id}', 0)
                examen_val = request.POST.get(f'examen_{eleve.id}', 0)
                
                # Conversion sécurisée en nombre décimal
                interro_val = float(interro_val) if interro_val else 0.0
                examen_val = float(examen_val) if examen_val else 0.0

                # Sauvegarder ou mettre à jour la note unique de l'élève pour ce cours
                NoteEleve.objects.update_or_create(
                    eleve=eleve,
                    cours_attribue=attribution_selectionnee,
                    defaults={
                        'note_interro': interro_val,
                        'note_examen': examen_val
                    }
                )
            
            messages.success(request, f"Les points pour le cours de {attribution_selectionnee.nom_cours} ont été envoyés avec succès !")
            return redirect(f"{request.path}?attribution={attribution_id}")

    context = {
        'cours': cours, # Garde le nom exact utilisé par ton template actuel pour ne rien casser
        'attribution_selectionnee': attribution_selectionnee,
        'eleves': eleves,
        'notes_existantes': notes_existantes,
    }
    return render(request, 'core/dashboard_professeur.html', context)

@login_required
def dashboard_eleve(request):
    if request.user.role != 'eleve':
        return redirect('aiguillage')
    situation, created = SituationEleve.objects.get_or_create(eleve=request.user)
    return render(request, 'core/dashboard_eleve.html', {'situation': situation})

@login_required
def modifier_profil(request):
    user = request.user
    
    if request.method == 'POST':
        # 1. Récupération des données du formulaire HTML
        last_name = request.POST.get('last_name')
        first_name = request.POST.get('first_name')
        email = request.POST.get('email')
        photo = request.FILES.get('photo_profil')
        
        # 2. Mise à jour des champs de l'utilisateur connecté
        if last_name:
            user.last_name = last_name
        if first_name:
            user.first_name = first_name
        if email:
            user.email = email
        if photo:
            user.photo_profil = photo
            
        # 3. Sauvegarde dans la base de données
        user.save()
        
        messages.success(request, "Votre profil a été mis à jour avec succès !")
        return redirect('aiguillage') # Redirige vers le nom exact défini dans ton urls.py
        
    # En mode GET, on passe simplement l'utilisateur connecté pour le contexte si nécessaire
    return render(request, 'core/modifier_profil.html')

class DashboardAiguillageView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        role = request.user.role
        if role == 'prefet':
            return redirect('dashboard_prefet')
        elif role == 'professeur':
            return redirect('dashboard_professeur')
        elif role == 'eleve':
            return redirect('dashboard_eleve')
        elif role == 'dir_discipline':
            return redirect('dashboard_discipline')
        # Ajoutez les autres rôles ici
        else:
            return render(request, 'core/dashboard_generique.html')


# =========================================================================
# 2. PORTAIL DISCIPLINE (CBV)
# =========================================================================
class DashboardDisciplineView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboard_discipline.html'

    # Sécurité : Vérifie si l'utilisateur à le droit d'accéder à cette classe
    def test_func(self):
        return self.request.user.role in ['dir_discipline', 'superadmin']

    def handle_no_permission(self):
        return redirect('aiguillage')

    # Gestion de l'affichage (GET)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['annonces'] = AnnonceEcole.objects.all().order_by('-cree_le')
        context['sanctions'] = SanctionEleve.objects.filter(actif=True).order_by('-date_debut')
        context['eleves'] = Utilisateur.objects.filter(role='eleve')
        return context

    # Traitement des formulaires (POST)
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        # Action A : Créer une annonce école (Vacances, Fériés, Info)
        if action == 'creer_annonce':
            AnnonceEcole.objects.create(
                titre=request.POST.get('titre'),
                contenu=request.POST.get('contenu'),
                type_annonce=request.POST.get('type_annonce'),
                date_evenement=request.POST.get('date_evenement') or None
            )
            messages.success(request, "L'annonce officielle a été publiée.")

        # Action B : Sanctionner un élève (Retard, Puni, Exclu)
        elif action == 'sanctionner_eleve':
            eleve_id = request.POST.get('eleve_id')
            eleve_concerne = get_object_or_404(Utilisateur, id=eleve_id, role='eleve')
            SanctionEleve.objects.create(
                eleve=eleve_concerne,
                type_sanction=request.POST.get('type_sanction'),
                motif=request.POST.get('motif'),
                date_fin=request.POST.get('date_fin') or None
            )
            messages.success(request, f"Mesure disciplinaire enregistrée pour {eleve_concerne.get_full_name()}.")

        return redirect('dashboard_discipline')


# =========================================================================
# 3. PORTAIL ELEVE CONVERTI EN CBV
# =========================================================================
class DashboardEleveView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboard_eleve' # <-- CORRECTION 1 : Enlever le .html si tu gères l'extension autrement, ou laisse 'core/dashboard_eleve.html' selon tes habitudes de rendu

    def test_func(self):
        # Vérifie que l'utilisateur est connecté ET qu'il a le rôle élève
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', None) == 'eleve'

    def handle_no_permission(self):
        # Si c'est un administrateur connecté, on le redirige plutôt vers l'admin au lieu de boucler
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return redirect('/admin/')
        return redirect('aiguillage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # CORRECTION 2 : Sécurité sur le modèle lié à l'Élève
        # Si ton modèle SituationEleve pointe vers un modèle "Eleve" spécifique et non directement vers "User",
        # assure-toui que self.request.user possède cette relation (ex: self.request.user.eleve)
        try:
            # Remplacer eleve=self.request.user par la relation appropriée si nécessaire
            situation, created = SituationEleve.objects.get_or_create(eleve=self.request.user)
            context['situation'] = situation
        except Exception:
            context['situation'] = None

        # Récupération des données du portail
        context['annonces'] = AnnonceEcole.objects.all().order_by('-cree_le')
        context['mes_sanctions'] = SanctionEleve.objects.filter(eleve=self.request.user, actif=True)
        
        return context
# =========================================================================
# 1. PORTAIL DU DIRECTEUR DES ÉTUDES (CBV)
# =========================================================================
class DashboardDirEtudesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboard_dir_etudes.html'

    def test_func(self):
        return self.request.user.role in ['dir_etudes', 'superadmin']

    def handle_no_permission(self):
        return redirect('aiguillage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Liste de tous les cours avec suivi de l'assiduité
        context['tous_les_cours'] = CoursAttribue.objects.all().select_related('professeur')
        # Liste des professeurs disponibles pour le formulaire d'attribution
        context['professeurs'] = Utilisateur.objects.filter(role='professeur')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'attribuer_cours':
            prof_id = request.POST.get('professeur_id')
            prof = get_object_or_404(Utilisateur, id=prof_id, role='professeur')
            
            CoursAttribue.objects.create(
                professeur=prof,
                nom_cours=request.POST.get('nom_cours'),
                classe=request.POST.get('classe'),
                heures_attribuees=request.POST.get('heures_attribuees')
            )
            messages.success(request, f"Le cours a été attribué avec succès au Professeur {prof.last_name}.")
        
        return redirect('aiguillage')


# =========================================================================
# 2. PORTAIL PROFESSEUR (CBV)
# =========================================================================
class DashboardProfesseurView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboard_professeur.html'

    def test_func(self):
        return self.request.user.role == 'professeur'

    def handle_no_permission(self):
        return redirect('aiguillage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # On affiche uniquement les cours de l'enseignant connecté
        context['mes_cours'] = CoursAttribue.objects.filter(professeur=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'cocher_heure':
            cours_id = request.POST.get('cours_id')
            # Sécurité renforcée : le cours doit appartenir au prof connecté
            cours = get_object_or_404(CoursAttribue, id=cours_id, professeur=self.request.user)
            
            if cours.heures_effectuees < cours.heures_attribuees:
                cours.heures_effectuees += 1
                cours.save()
                messages.success(request, f"Une heure de cours validée pour : {cours.nom_cours} ({cours.classe}).")
            else:
                messages.error(request, "Le quota d'heures maximum attribué à ce cours est déjà atteint.")

        return redirect('dashboard_professeur')
# =========================================================================
# PORTAIL DU SECRÉTARIAT ADMINISTRATIF (CBV)
# =========================================================================
class DashboardSecretaireView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboard_secretaire.html'

    def test_func(self):
        return self.request.user.role in ['secretaire', 'superadmin']

    def handle_no_permission(self):
        return redirect('aiguillage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        
        # Récupération des filtres de recherche (GET)
        search_query = request.GET.get('search', '').strip()
        
        # Gestion de la liste des élèves avec ou sans recherche
        eleves_qs = Utilisateur.objects.filter(role='eleve')
        if search_query:
            eleves_qs = eleves_qs.filter(
                Q(first_name__icontains=search_query) | 
                Q(last_name__icontains=search_query) | 
                Q(matricule__icontains=search_query)
            )
        
        context['eleves'] = eleves_qs.order_by('last_name')
        context['professeurs'] = Utilisateur.objects.filter(role='professeur').order_by('last_name')
        context['search_query'] = search_query
        
        # Statistiques rapides pour le secrétariat
        context['total_eleves'] = Utilisateur.objects.filter(role='eleve').count()
        context['total_professeurs'] = Utilisateur.objects.filter(role='professeur').count()
        context['sanctions_actives'] = SanctionEleve.objects.filter(actif=True).count()
        
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        # Le secrétariat peut modifier des informations d'urgence ou valider un dossier administratif
        if action == 'modifier_fiche_eleve':
            eleve_id = request.POST.get('eleve_id')
            eleve = get_object_or_404(Utilisateur, id=eleve_id, role='eleve')
            
            eleve.first_name = request.POST.get('first_name')
            eleve.last_name = request.POST.get('last_name')
            eleve.email = request.POST.get('email')
            eleve.matricule = request.POST.get('matricule')
            eleve.save()
            
            messages.success(request, f"La fiche administrative de {eleve.get_full_name()} a été mise à jour.")
            
        return redirect('dashboard_secretaire')
    
class DashboardReceptionnisteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboard_receptionniste.html'

    def test_func(self):
        return self.request.user.role in ['receptionniste', 'superadmin']

    def handle_no_permission(self):
        return redirect('aiguillage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Afficher les 10 derniers élèves inscrits pour un suivi rapide
        context['derniers_eleves'] = Utilisateur.objects.filter(role='eleve').order_by('-date_joined')[:10]
        return context

    def post(self, request, *args, **kwargs):
        # Récupération des données de base du formulaire d'inscription
        first_name = request.POST.get('first_name').strip()
        last_name = request.POST.get('last_name').strip()
        
        # AJOUT : Récupération des critères de tri pour les classes et options
        classe_choisie = request.POST.get('classe')
        section_choisie = request.POST.get('section')
        promotion_choisie = request.POST.get('promotion')

        # # 1. Génération automatique d'un matricule unique (Ex: BB-2026-XXXX)
        annee_actuelle = 2026
        num_aleatoire = random.randint(1000, 9999)
        matricule = f"BB-{annee_actuelle}-{num_aleatoire}"

        # Vérification d'unicité au cas où
        while Utilisateur.objects.filter(matricule=matricule).exists():
            num_aleatoire = random.randint(1000, 9999)
            matricule = f"BB-{annee_actuelle}-{num_aleatoire}"

        # # 2. Génération automatique de l'email de l'école
        email_username = f"{first_name.lower().replace(' ', '')}.{last_name.lower().replace(' ', '')}"
        email_ecole = f"{email_username}@bonberger.edu"

        # Gestion des doublons d'homonymes pour l'email
        if Utilisateur.objects.filter(email=email_ecole).exists():
            email_ecole = f"{email_username}{random.randint(1, 9)}@bonberger.edu"

        # # 3. Création de l'utilisateur Élève avec ses attributs scolaires complets
        nouvel_eleve = Utilisateur.objects.create_user(
            username=email_ecole,  # Le username sert à la connexion via l'adresse mail
            email=email_ecole,
            first_name=first_name,
            last_name=last_name,
            role='eleve',
            matricule=matricule,
            # Sauvegarde des nouveaux critères d'organisation
            classe=classe_choisie,
            section=section_choisie,
            promotion=promotion_choisie
        )

        # Note : `.create_user` gère déjà le chiffrement.
        # Le matricule devient le mot de passe par défaut via la logique de notre modèle.
        nouvel_eleve.set_password(matricule)
        nouvel_eleve.save()

        # # 4. Initialisation automatique de sa fiche financière vide
        SituationEleve.objects.create(eleve=nouvel_eleve, solde_financier=0.00)

        messages.success(
            request,
            f"Inscription réussie ! Élève : {last_name} {first_name}. "
            f"Email : {email_ecole} | Matricule/Password : {matricule}"
        )
        return redirect('dashboard_receptionniste')
    
# =========================================================================
# PORTAIL DE LA COMPTABILITÉ (CBV)
# =========================================================================
class DashboardComptableView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboard_comptable.html'

    def test_func(self):
        return self.request.user.role in ['comptable', 'superadmin']

    def handle_no_permission(self):
        return redirect('aiguillage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupération de toutes les fiches financières des élèves
        situations = SituationEleve.objects.select_related('eleve').order_by('eleve__last_name')
        context['situations'] = situations
        
        # Calcul des statistiques globales pour le bandeau comptable
        context['total_dettes'] = situations.aggregate(Sum('solde_financier'))['solde_financier__sum'] or 0.00
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'enregistrer_paiement':
            situation_id = request.POST.get('situation_id')
            montant_verse = float(request.POST.get('montant', 0))
            
            # Récupération sécurisée de la fiche financière
            situation = get_object_or_404(SituationEleve, id=situation_id)
            
            if montant_verse > 0:
                # Soustraction du montant versé du solde débiteur de l'élève
                ancien_solde = situation.solde_financier
                situation.solde_financier = max(0.00, float(ancien_solde) - montant_verse)
                situation.save()
                
                messages.success(
                    request, 
                    f"Paiement de {montant_verse} USD enregistré pour {situation.eleve.get_full_name()}. "
                    f"Nouveau solde : {situation.solde_financier} USD."
                )
            else:
                messages.error(request, "Le montant du versement doit être supérieur à 0.")

        return redirect('dashboard_comptable')
def get_queryset(self):
    query = self.request.GET.get('q')
    # On exclut le superadmin connecté
    queryset = Utilisateur.objects.exclude(id=self.request.user.id).order_size() # ou .order_by('role')
    
    if query:
        queryset = queryset.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query)
        )
    return queryset
class ConnexionPortailView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True # Si déjà connecté, renvoie directement à l'aiguillage

    def get_success_url(self):
        # Redirige vers le nom de la route d'aiguillage
        return reverse_lazy('aiguillage')

class DeconnexionPortailView(LogoutView):
    pass # Redirige vers la page de login après déconnexion

class AccueilVitrineView(TemplateView):
    template_name = 'core/accueil.html'

# 1. VUE D'INSCRIPTION PUBLIQUE
class InscriptionView(CreateView):
    model = Utilisateur
    form_class = InscriptionPersonnelForm
    template_name = 'core/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.username = user.email  # Django utilise le username, on y met l'email
        user.set_password(form.cleaned_data['password'])
        user.role = 'en_attente'     # Sécurité : aucun rôle par défaut
        user.save()
        messages.success(self.request, "Votre demande de compte a été soumise. Attendez la validation du Préfet.")
        return super().form_valid(form)

# 2. VUE INTERFACE SUPERADMIN (GESTION DES RÔLES)
class DashboardSuperadminView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Utilisateur
    template_name = 'core/dashboard_superadmin.html'
    context_object_name = 'utilisateurs'

    def test_func(self):
        return self.request.user.role == 'superadmin' or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('aiguillage')

    def get_queryset(self):
        # On affiche tout le monde sauf le superadmin connecté
        return Utilisateur.objects.exclude(id=self.request.user.id).order_by('role', 'last_name')

    def post(self, request, *args, **kwargs):
        # Action de changement de rôle
        user_id = request.POST.get('user_id')
        nouveau_role = request.POST.get('role')
        
        personnel = get_object_or_404(Utilisateur, id=user_id)
        personnel.role = nouveau_role
        personnel.save()
        
        messages.success(request, f"Le rôle de {personnel.get_full_name()} a été modifié en [{nouveau_role}].")
        return redirect('dashboard_superadmin')

@login_required
def supprimer_utilisateur(request, user_id):
    if request.user.role != 'prefet' and request.user.role != 'superadmin':
        messages.error(request, "Action non autorisée.")
        return redirect('dashboard_superadmin')
        
    personnel = get_object_or_404(Utilisateur, id=user_id)
    nom_complet = personnel.get_full_name() or personnel.email
    personnel.delete()
    
    messages.success(request, f"L'utilisateur {nom_complet} a été supprimé définitivement.")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_aiguillage'))

def get_queryset(self):
        # 1. On récupère les paramètres de la barre de recherche et des boutons de la sidebar
        query = self.request.GET.get('q')
        filtre = self.request.GET.get('filtre')
        
        # Base : tout le monde sauf le superadmin connecté
        queryset = Utilisateur.objects.exclude(id=self.request.user.id).order_by('role', 'last_name')
        
        # 2. Gestion du filtrage par les boutons de la Sidebar
        if filtre == 'eleve':
            queryset = queryset.filter(role='eleve')
        elif filtre == 'admin':
            # On affiche les préfets, comptables, dir. discipline, ou superadmins
            queryset = queryset.filter(role__in=['prefet', 'comptable', 'superadmin'])
            
        # 3. Gestion de la barre de recherche textuelle (si présente)
        if query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(first_name__icontains=query) | 
                Q(last_name__icontains=query) | 
                Q(email__icontains=query)
            )
            
        return 
# Dans core/views.py

def nos_valeurs(request):
    return render(request, 'core/nos_valeurs.html')

def contact(request):
    return render(request, 'core/contact.html')

@login_required
def mes_cours_eleve(request):
    # Plus tard, tu pourras récupérer dynamiquement les cours de l'élève ici
    return render(request, 'core/mes_cours.html')

@login_required
def resultats_eleve(request):
    # Plus tard, tu pourras récupérer dynamiquement les notes/bulletins ici
    return render(request, 'core/resultats_academiques.html')

@login_required
def liste_professeurs(request):  # <--- Vérifie bien l'orthographe exacte ici
    if request.user.role not in ['dir_etudes', 'superadmin', 'prefet']:
        return redirect('aiguillage')
        
    professeurs = Utilisateur.objects.filter(role='professeur')
    attributions = CoursAttribue.objects.all()

    context = {
        'professeurs': professeurs,
        'attributions': attributions,
    }
    return render(request, 'core/liste_professeurs.html', context)

@login_required
def charger_fiche_notation(request, cours_id):
    cours = get_object_or_404(CoursAttribue, id=cours_id)
    
    # Récupération des élèves de la classe correspondante
    eleves = Utilisateur.objects.filter(role='eleve', classe__iexact=cours.classe).order_by('last_name')
    
    # Traitement lors de l'enregistrement des notes (requête POST)
    if request.method == 'POST':
        # On récupère les barèmes saisis en tête de formulaire
        max_int = request.POST.get('max_interro', 20)
        max_ex = request.POST.get('max_examen', 40)
        
        for eleve in eleves:
            # On récupère les valeurs des inputs HTML
            val_interro = request.POST.get(f"interro_{eleve.id}", 0.0)
            val_examen = request.POST.get(f"examen_{eleve.id}", 0.0)
            
            # Si les cases sont vides, on met 0.0 par défaut pour éviter les plantages
            val_interro = float(val_interro) if val_interro != "" else 0.0
            val_examen = float(val_examen) if val_examen != "" else 0.0
            
            # update_or_create respecte la contrainte 'unique_together' de ton modèle
            NoteEleve.objects.update_or_create(
                eleve=eleve,
                cours_attribue=cours,
                defaults={
                    'note_interro': val_interro,
                    'note_examen': val_examen,
                    'max_interro': max_int,
                    'max_examen': max_ex
                }
            )
        return HttpResponse("<div class='status-alert' style='background:var(--success); padding:10px; border-radius:6px; color:white;'>Grille de notes enregistrée avec succès !</div>")

    # Récupération des notes existantes pour les pré-remplir dans les cases si elles existent
    # On crée un dictionnaire {eleve_id: objet_note} pour un accès rapide dans le template
    notes_existantes = {note.eleve_id: note for note in NoteEleve.objects.filter(cours_attribue=cours)}

    html = render_to_string('core/includes/fiche_notation.html', {
        'cours': cours,
        'eleves': eleves,
        'notes_existantes': notes_existantes,
    }, request=request)
    
    return HttpResponse(html)

@login_required
def liste_classes_professeur(request):
    # 1. On récupère toutes les attributions du professeur connecté
    attributions = CoursAttribue.objects.filter(professeur=request.user)

    # 2. On isole les classes uniques enseignées
    classes_enseignees = attributions.values_list('classe', flat=True).distinct()

    # 3. Interception des filtres de l'URL
    attribution_id = request.GET.get('attribution')
    classe_selectionnee = request.GET.get('classe_selectionnee')
    
    attribution_selectionnee = None
    eleves = []
    titre_panneau = ""
    
    from core.models import Utilisateur

    # Cas A : Clic sur un cours spécifique (colonne de gauche)
    if attribution_id:
        try:
            attribution_selectionnee = CoursAttribue.objects.get(id=attribution_id, professeur=request.user)
            eleves = Utilisateur.objects.filter(role='eleve', classe__iexact=attribution_selectionnee.classe).order_by('promotion', 'section', 'last_name')
            titre_panneau = f"Encodage des Points : {attribution_selectionnee.nom_cours} ({attribution_selectionnee.classe})"
        except CoursAttribue.DoesNotExist:
            pass

    # Cas B : Clic sur le bouton bleu "Voir les Élèves" d'une classe (panneau central)
    elif classe_selectionnee:
        eleves = Utilisateur.objects.filter(role='eleve', classe__iexact=classe_selectionnee).order_by('promotion', 'section', 'last_name')
        titre_panneau = f"Liste des Élèves de la classe : {classe_selectionnee}"

    return render(request, 'core/dashboard_professeur.html', {
        'cours': attributions,
        'classes_enseignees': classes_enseignees,
        'attribution_selectionnee': attribution_selectionnee,
        'classe_selectionnee': classe_selectionnee, # Transmis pour le contrôle d'affichage
        'eleves': eleves,
        'titre_panneau': titre_panneau,
    })

@login_required
def charger_eleves_par_classe(request):
    nom_classe = request.GET.get('classe')
    
    # Récupération des élèves appartenant à cette classe
    eleves = Utilisateur.objects.filter(
        role='eleve', 
        classe__iexact=nom_classe
    ).order_by('promotion', 'section', 'last_name')
    
    # On passe les données au morceau de template
    html = render_to_string('core/includes/tableau_eleves_classe.html', {
        'classe': nom_classe,
        'eleves': eleves,
    }, request=request)
    
    return HttpResponse(html)

@login_required
def espace_eleve_paiement(request):
    # Vérification de sécurité pour s'assurer que c'est un élève
    if request.user.role != 'eleve':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    # 1. Récupérer le montant total dû pour la classe/promotion/section de l'élève
    frais_classe = FraisScolaire.objects.filter(
        classe__iexact=request.user.classe,
        promotion__iexact=request.user.promotion,
        section__iexact=request.user.section
    ).first()
    
    montant_total_du = frais_classe.montant_total if frais_classe else 0

    # 2. Récupérer l'historique des paiements de l'élève
    mes_versements = Paiement.objects.filter(eleve=request.user).order_by('-date_paiement')

    # 3. Calculer le total déjà payé
    total_paye = mes_versements.aggregate(Sum('montant_verse'))['montant_verse__sum'] or 0

    # 4. Calculer le reste à payer
    reste_a_payer = montant_total_du - total_paye

    # Calcul du pourcentage pour une jolie barre de progression
    pourcentage_paye = 0
    if montant_total_du > 0:
        pourcentage_paye = int((total_paye / montant_total_du) * 100)

    context = {
        'montant_total_du': montant_total_du,
        'total_paye': total_paye,
        'reste_a_payer': reste_a_payer,
        'pourcentage_paye': pourcentage_paye,
        'mes_versements': mes_versements,
    }
    
@login_required
def espace_eleve_paiement(request):
    if request.user.role != 'eleve':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    # Traitement de l'envoi du bordereau par l'élève
    if request.method == 'POST' and request.FILES.get('bordereau'):
        montant = request.POST.get('montant_verse')
        motif = request.POST.get('motif', 'Frais Scolaires')
        fichier = request.FILES.get('bordereau')
        
        if montant:
            Paiement.objects.create(
                eleve=request.user,
                montant_verse=montant,
                motif=motif,
                bordereau=fichier,
                statut='attente',
                recu_numero=f"REQ-{uuid.uuid4().hex[:8].upper()}" # Numéro temporaire
            )
            messages.success(request, "Votre bordereau a bien été soumis à l'administrateur financier pour vérification.")
            return redirect('espace_eleve_paiement')

    # 1. Récupérer le montant total dû
    frais_classe = FraisScolaire.objects.filter(
        classe__iexact=request.user.classe,
        promotion__iexact=request.user.promotion,
        section__iexact=request.user.section
    ).first()
    montant_total_du = frais_classe.montant_total if frais_classe else 0

    # 2. Historique complet (Trié du plus récent au plus ancien)
    mes_versements = Paiement.objects.filter(eleve=request.user).order_by('-date_paiement')

    # 3. Calculer uniquement ce qui a été VALIDÉ par le financier
    total_paye = mes_versements.filter(statut='valide').aggregate(Sum('montant_verse'))['montant_verse__sum'] or 0

    # 4. Reste à payer basé sur les validations réelles
    reste_a_payer = montant_total_du - total_paye

    pourcentage_paye = 0
    if montant_total_du > 0:
        pourcentage_paye = int((total_paye / montant_total_du) * 100)

    context = {
        'montant_total_du': montant_total_du,
        'total_paye': total_paye,
        'reste_a_payer': reste_a_payer,
        'pourcentage_paye': pourcentage_paye,
        'mes_versements': mes_versements,
    }
    return render(request, 'core/espace_eleve_paiement.html', context)