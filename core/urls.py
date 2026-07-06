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
    path('portail', views.dashboard_aiguillage, name='aiguillage'),
    path('portail/superadmin/', DashboardSuperadminView.as_view(), name='dashboard_superadmin'),
    path('prefet/', views.dashboard_prefet, name='dashboard_prefet'),
    path('professeur/', views.dashboard_professeur, name='dashboard_professeur'),
    path('eleve/', views.dashboard_eleve, name='dashboard_eleve'),
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
    # Connexion et déconnexion
    path('login/', ConnexionPortailView.as_view(), name='login'),
    path('logout/', DeconnexionPortailView.as_view(), name='logout'),

    
    # Authentification native de Django
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
