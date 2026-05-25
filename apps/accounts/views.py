from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Follow
from .serializers import ProfileSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        profile_data = request.data.get("profile", request.data)
        profile_ser = ProfileSerializer(
            self.request.user.profile, data=profile_data, partial=True
        )
        profile_ser.is_valid(raise_exception=True)
        profile_ser.save()
        return Response(UserSerializer(self.request.user).data)


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.select_related("profile").all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class FollowView(APIView):
    def post(self, request, user_id: int):
        followee = get_object_or_404(User, id=user_id)
        if followee == request.user:
            return Response({"detail": "Cannot follow yourself."},
                            status=status.HTTP_400_BAD_REQUEST)
        Follow.objects.get_or_create(follower=request.user, followee=followee)
        return Response({"status": "followed"}, status=status.HTTP_201_CREATED)

    def delete(self, request, user_id: int):
        Follow.objects.filter(follower=request.user, followee_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
