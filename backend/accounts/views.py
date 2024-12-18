from django.contrib.auth import get_user_model, authenticate

from .serializers import UsersSerializer, SignInSerializer
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics, status
from django.contrib.auth.models import User
from rest_framework import permissions
from django.http import JsonResponse
from accounts.main import run_conversation, gpt_speech
import logging
import dotenv
import os

from openai import OpenAI
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse
import tempfile


client = OpenAI()

User = get_user_model()

logger = logging.getLogger(__name__)


class UserCreate(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("Validation Errors:", serializer.errors)  # Log the errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignInView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            return Response(
                {
                    "message": "Login successful!",
                    "user": {"username": user.username, "email": user.email},
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST
            )


# server neo4j
load_status = dotenv.load_dotenv("variables.txt")
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
USR = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
config = {
    "graph_store": {
        "provider": "neo4j",
        "config": {"url": URI, "username": USR, "password": PASSWORD},
    },
    "version": "v1.1",
}


@api_view(["POST"])
def start_conversation(request):
    print("Reached start_conversation")
    mem0_user_id = "mustafa_gumustas"
    first_run = request.data.get("first_run", True)
    audio_base64 = request.data.get("audio_base64")
    conversation = run_conversation(mem0_user_id, first_run, audio_base64=audio_base64)
    return JsonResponse({"text": conversation})


@csrf_exempt
def generate_speech(request):
    text = request.POST.get("text")
    print("Received text:", text)  # Log the text received from the frontend
    if not text:
        return JsonResponse({"error": "No text provided"}, status=400)

    try:
        # Generate TTS and save to a temporary file
        with client.audio.speech.create(
            model="tts-1", voice="alloy", input=text
        ) as response:
            # Create a temporary file and write the response content
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name

        # Serve the temporary file as a FileResponse
        return FileResponse(open(temp_file_path, "rb"), content_type="audio/mpeg")

    except Exception as e:
        print("Error generating TTS:", str(e))
        return JsonResponse({"error": "Failed to generate speech"}, status=500)
    finally:
        # Optional: Cleanup the temporary file after serving
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
