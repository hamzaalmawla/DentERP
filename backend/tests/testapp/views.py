from dataclasses import asdict

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import container
from apps.core.api.serializers import BaseModelSerializer
from apps.core.application.dtos import Actor
from apps.core.domain.errors import ConflictError, DomainError, HardDeleteError

from .models import Note
from .queries import NoteQueries, OrmNoteRepository


class DomainErrorView(APIView):
    def get(self, request):
        raise HardDeleteError()


class DomainErrorWithParamsView(APIView):
    def get(self, request):
        raise DomainError("too_many", "At most %(limit)s chairs.", {"limit": 3})


class ConflictView(APIView):
    def get(self, request):
        raise ConflictError("already_approved", "Already approved.")


class NameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=5)


class ValidationView(APIView):
    def post(self, request):
        NameSerializer(data=request.data).is_valid(raise_exception=True)
        return Response({})


class DjangoValidationView(APIView):
    def get(self, request):
        raise DjangoValidationError({"due": ["Bad date."]})


class NotFoundView(APIView):
    def get(self, request):
        raise Http404("No Note matches the given query.")


class PermissionDeniedView(APIView):
    def get(self, request):
        raise PermissionDenied


class NoteSerializer(BaseModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "title", "created_at"]


class NoteListView(generics.ListAPIView):
    queryset = Note.objects.order_by("id")
    serializer_class = NoteSerializer
    filterset_fields = ["title"]
    ordering_fields = ["title", "id"]


class ScopedNoteView(APIView):
    def get(self, request, pk: int):
        actor = Actor(request.user.pk, request.headers.get("X-Active-Role", ""))
        return Response(asdict(NoteQueries(OrmNoteRepository()).get(actor, pk)))


class NoteCreateView(APIView):
    """Creates a note and audits it, as a module's service would."""

    def post(self, request):
        note = Note.objects.create(title=request.data["title"])
        container.audit_logger().log(
            "create", model=Note._meta.label, object_id=note.pk, changes={"title": note.title}
        )
        return Response({"id": note.pk}, status=201)
