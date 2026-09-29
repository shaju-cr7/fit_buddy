from django.contrib import admin
from django.urls import path

from plans import views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", views.page, {"template": "index.html"}, name="home"),
    path("profile/", views.page, {"template": "profile.html"}, name="profile"),
    path("result/", views.page, {"template": "result.html"}, name="result"),
    path("plan/", views.page, {"template": "plan.html"}, name="plan"),
    path("nutrition/", views.page, {"template": "nutrition.html"}, name="nutrition"),
    path("tips/", views.page, {"template": "tips.html"}, name="tips"),
    path("feedback/", views.page, {"template": "feedback.html"}, name="feedback"),
    path("dashboard/", views.page, {"template": "dashboard.html"}, name="dashboard"),
    path("login/", views.page, {"template": "login.html"}, name="login"),
    path("register/", views.page, {"template": "register.html"}, name="register"),
    path("admin/", views.admin_page, name="admin-dashboard"),
    path("api/auth/register/", views.register, name="api-register"),
    path("api/auth/login/", views.login, name="api-login"),
    path("api/auth/logout/", views.logout, name="api-logout"),
    path("api/me/", views.me, name="api-me"),
    path("api/profile/", views.profile, name="api-profile"),
    path("api/plan/", views.latest_plan, name="api-plan"),
    path("api/plan/<int:plan_id>/", views.get_plan, name="api-plan-detail"),
    path("api/feedback/", views.feedback, name="api-feedback"),
    path("api/progress/", views.progress, name="api-progress"),
    path("api/tips/", views.tips, name="api-tips"),
    path("api/admin/stats/", views.admin_stats, name="api-admin-stats"),
]