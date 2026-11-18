from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/google/", views.GoogleLoginView.as_view(), name="auth-google"),
    path("auth/refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/password/reset/", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("auth/password/reset/confirm/", views.PasswordResetConfirmView.as_view(), name="auth-password-confirm"),
    path("auth/email/verify/", views.EmailVerifyView.as_view(), name="auth-email-verify"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/password/", views.PasswordChangeView.as_view(), name="me-password"),
    path("me/email/verify/", views.EmailVerifyResendView.as_view(), name="me-email-verify"),
    path("me/2fa/setup/", views.TwoFactorSetupView.as_view(), name="me-2fa-setup"),
    path("me/2fa/enable/", views.TwoFactorEnableView.as_view(), name="me-2fa-enable"),
    path("me/2fa/disable/", views.TwoFactorDisableView.as_view(), name="me-2fa-disable"),
]
