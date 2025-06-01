from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'recruiters', views.RecruiterProfileViewSet, basename='recruiter')
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'active-roles', views.ActiveRoleViewSet, basename='active-role')
router.register(r'workflows', views.WorkflowViewSet, basename='workflow')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.RecruiterRegistrationView.as_view(), name='recruiter-register'),
    path('login/', views.RecruiterLoginView.as_view(), name='recruiter-login'),
    path('auth/profile/', views.RecruiterProfileView.as_view(), name='recruiter-profile'),
    path('auth/profile/update/', views.RecruiterProfileUpdateView.as_view(), name='recruiter-profile-update'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='recruiter-change-password'),
]