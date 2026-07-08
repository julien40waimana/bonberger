from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (DashboardAiguillageView,
                    DashboardDisciplineView, 
                    DashboardEleveView,
                    DashboardDirEtudesView,
                    DashboardProfesseurView,
                    DashboardSecretaireView,
                    DashboardReceptionnisteView,
                    DashboardComptableView,
                    ConnexionPortailView,
                    DeconnexionPortailView,
                    AccueilVitrineView,
                    InscriptionView,
                    DashboardSuperadminView)
from . import views

urlpatterns = [
    path('portail/', views.dashboard_aiguillage, name='aiguillage'),
    path('portail/direction-etudes/', views.DashboardDirEtudesView.as_view(), name='dashboard_dir_etudes'),
    path('portail/superadmin/', DashboardSuperadminView.as_view(), name='dashboard_superadmin'),
    path('prefet/', views.dashboard_prefet, name='dashboard_prefet'),
    path('professeur/', views.dashboard_professeur, name='dashboard_professeur'),
    path('eleve/', views.dashboard_eleve, name='dashboard_eleve'),
    path('eleve/mes-cours/', views.mes_cours_eleve, name='mes_cours_eleve'),
    path('eleve/resultats/', views.resultats_eleve, name='resultats_eleve'),
    path('discipline/', DashboardDisciplineView.as_view(), name='dashboard_discipline'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('secretariat/', DashboardSecretaireView.as_view(), name='dashboard_secretaire'),
    path('reception/', DashboardReceptionnisteView.as_view(), name='dashboard_receptionniste'),
    path('comptabilite/', DashboardComptableView.as_view(), name='dashboard_comptable'),
    path('', AccueilVitrineView.as_view(), name='accueil'),
    path('inscription/', InscriptionView.as_view(), name='register'),
    path('direction-general/', DashboardSuperadminView.as_view(), name='dashboard_superadmin'),
    path('utilisateur/supprimer/<int:user_id>/', views.supprimer_utilisateur, name='supprimer_utilisateur'),
    path('nos-valeurs/', views.nos_valeurs, name='nos_valeurs'),
    path('contact/', views.contact, name='contact'),
    path('liste-professeurs/', views.liste_professeurs, name='liste_professeurs'),
    path('ajax/charger-fiche-notation/<int:cours_id>/', views.charger_fiche_notation, name='charger_fiche_notation'),
    path('ajax/mes-classes/', views.liste_classes_professeur, name='ajax_mes_classes'),
    path('ajax/classe/eleves/', views.charger_eleves_par_classe, name='ajax_eleves_classe'),
    path('professeur/mes-classes/', views.liste_classes_professeur, name='liste_classes_professeur'),
    path('eleve/mes-paiements/', views.espace_eleve_paiement, name='espace_eleve_paiement'),
    # Connexion et déconnexion
    path('login/', ConnexionPortailView.as_view(), name='login'),
    path('logout/', DeconnexionPortailView.as_view(), name='logout'),

    
    # Authentification native de Django
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
