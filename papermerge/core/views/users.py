import logging

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from rest_framework_json_api.views import ModelViewSet

from papermerge.core.serializers import (UserSerializer, PasswordSerializer)
from papermerge.core.models import User
from .mixins import RequireAuthMixin

logger = logging.getLogger(__name__)


class UsersViewSet(RequireAuthMixin, ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserChangePassword(RequireAuthMixin, APIView):
    parser_classes = [JSONParser]

    def post(self, request, pk):
        serializer = PasswordSerializer(data=request.data)
        user = User.objects.get(pk=pk)
        if serializer.is_valid():
            user.set_password(serializer.validated_data['password'])
            user.save()
            return Response({'status': 'password set'})
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
