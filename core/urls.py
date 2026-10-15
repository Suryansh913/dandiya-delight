from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_view, name="verify"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("browse/", views.browse, name="browse"),
    path("p/<int:user_id>/", views.profile_detail, name="profile_detail"),
    path("interest/<int:user_id>/", views.send_interest, name="send_interest"),
    path("respond/<int:pk>/<str:action>/", views.respond, name="respond"),
    path("inbox/", views.inbox, name="inbox"),
    path("manage/", views.manage, name="manage"),
    path("manage/send/<int:pk>/", views.send_code, name="send_code"),
    path("chat/<int:user_id>/", views.chat, name="chat"),
    path("report/<int:user_id>/", views.report, name="report"),
]
