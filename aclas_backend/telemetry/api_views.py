from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .serializers import TelemetryEventSerializer
from .models import TelemetryEvent

class HeartbeatAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = TelemetryEventSerializer(data=request.data)
        if serializer.is_valid():
            TelemetryEvent.objects.create(
                user=request.user,
                **serializer.validated_data
            )
            return Response({"status": "Heartbeat recorded"}, status=201)
        return Response(serializer.errors, status=400)
