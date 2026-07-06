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
from .models import Utilisateur
from .forms import InscriptionPersonnelForm
from django.views.generic import CreateView, ListView
from django.shortcuts import render, redirect, get_object_or_404

@login_required
def dashboard_aiguillage(request):
    role = request.user.role
    if request.user.is_superuser or role == 'superadmin':
        return redirect('dashboard_superadmin')
    elif role == 'prefet':
        return redirect('dashboard_prefet')
    elif role == 'professeur':
        return redirect('dashboard_professeur')
    elif role == 'eleve':
        return redirect('dashboard_eleve')
    elif role == 'receptionniste':
        return redirect('dashboard_receptionniste')
    elif role == 'comptable':
        return redirect('dashboard_comptable')
    elif role == 'en_attente':
        return render(request, 'core/en_attente.html')
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
    if request.user.role != 'professeur':
        return redirect('aiguillage')
    cours = CoursAttribue.objects.filter(professeur=request.user)
    
    if request.method == 'POST':
        cours_id = request.POST.get('cours_id')
        action = request.POST.get('action')
        if action == "cocher_heure":
            c = CoursAttribue.objects.get(id=cours_id, professeur=request.user)
            c.heures_effectuees += 1
            c.save()
            messages.success(request, f"Heure validée pour le cours de {c.nom_cours}.")
            return redirect('dashboard_professeur')

    return render(request, 'core/dashboard_professeur.html', {'cours': cours})

@login_required
def dashboard_eleve(request):
    if request.user.role != 'eleve':
        return redirect('aiguillage')
    situation, created = SituationEleve.objects.get_or_create(eleve=request.user)
    return render(request, 'core/dashboard_eleve.html', {'situation': situation})

@login_required
def modifier_profil(request):
    if request.method == 'POST':
        # On passe les données POST, les fichiers (avatar) et l'instance de l'utilisateur connecté
        form = InscriptionPersonnelForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre profil a été mis à jour avec succès !")
            return redirect('dashboard_aiguillage') # Redirige vers ton aiguillage après succès
    else:
        # En mode GET, on charge le formulaire pré-rempli avec les infos actuelles de l'utilisateur
        form = InscriptionPersonnelForm(instance=request.user)
    
    # CRUCIAL : On envoie le 'form' dans le contexte pour que le HTML puisse l'afficher !
    return render(request, 'core/modifier_profil.html', {'form': form})

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
    template_name = 'core/dashboard_eleve.html'

    def test_func(self):
        return self.request.user.role == 'eleve'

    def handle_no_permission(self):
        return redirect('aiguillage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Situation financière et bulletin
        situation, created = SituationEleve.objects.get_or_create(eleve=self.request.user)
        context['situation'] = situation
        
        # Récupération des données du portail discipline pour l'élève connecté
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
        
        return redirect('dashboard_dir_etudes')


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
        # Récupération des données du formulaire d'inscription
        first_name = request.POST.get('first_name').strip()
        last_name = request.POST.get('last_name').strip()
        
        # 1. Génération automatique d'un matricule unique (Ex: BB-2026-XXXX)
        annee_actuelle = 2026
        num_aleatoire = random.randint(1000, 9999)
        matricule = f"BB-{annee_actuelle}-{num_aleatoire}"
        
        # Vérification d'unicité au cas où
        while Utilisateur.objects.filter(matricule=matricule).exists():
            num_aleatoire = random.randint(1000, 9999)
            matricule = f"BB-{annee_actuelle}-{num_aleatoire}"

        # 2. Génération automatique de l'email de l'école
        # Nettoyage simple des espaces pour l'email
        email_username = f"{first_name.lower().replace(' ', '')}.{last_name.lower().replace(' ', '')}"
        email_ecole = f"{email_username}@bonberger.edu"
        
        # Gestion des doublons d'homonymes pour l'email
        if Utilisateur.objects.filter(email=email_ecole).exists():
            email_ecole = f"{email_username}{random.randint(1, 9)}@bonberger.edu"

        # 3. Création de l'utilisateur Élève
        nouvel_eleve = Utilisateur.objects.create_user(
            username=email_ecole, # Le username sert à la connexion via l'adresse mail
            email=email_ecole,
            first_name=first_name,
            last_name=last_name,
            role='eleve',
            matricule=matricule
        )
        # Note : `.create_user` gère déjà le chiffrement. 
        # Le matricule devient le mot de passe par défaut via la logique de notre modèle.
        nouvel_eleve.set_password(matricule)
        nouvel_eleve.save()

        # 4. Initialisation automatique de sa fiche financière vide
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