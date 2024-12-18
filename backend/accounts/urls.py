from django.urls import path
from .views import (
    UserCreate,
    SignInView,
    start_conversation,
    generate_speech,
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("sign-up/", UserCreate.as_view(), name="sign_up"),
    path("sign-in/", SignInView.as_view(), name="sign-in"),
    path("start_conversation/", start_conversation, name="start_conversation"),
    path("generate_speech/", generate_speech, name="generate_speech"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
