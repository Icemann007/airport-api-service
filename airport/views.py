from rest_framework import viewsets

from airport.models import Airport, Route, Airplane, Crew, Flight, Order, AirplaneType
from airport.serializers import (
    AirportSerializer,
    RouteSerializer,
    AirplaneTypeSerializer,
    AirplaneSerializer,
    CrewSerializer,
    FlightSerializer,
    OrderSerializer,
    RouteListSerializer,
    RouteDetailSerializer,
    AirplaneListSerializer,
    FlightListSerializer,
    FlightDetailSerializer,
    OrderListSerializer,
)


class AirportViewSet(viewsets.ModelViewSet):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related("source", "destination")

    def get_queryset(self):
        queryset = super().get_queryset()
        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")

        if source:
            queryset = queryset.filter(source__closest_big_city__icontains=source)

        if destination:
            queryset = queryset.filter(
                destination__closest_big_city__icontains=destination
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer

        if self.action == "retrieve":
            return RouteDetailSerializer

        return RouteSerializer


class AirplaneTypeViewSet(viewsets.ModelViewSet):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer


class AirplaneViewSet(viewsets.ModelViewSet):
    queryset = Airplane.objects.select_related("airplane_type")

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AirplaneListSerializer

        return AirplaneSerializer


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer


class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.select_related("route", "airplane").prefetch_related(
        "crew"
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        departure_date = self.request.query_params.get("departure_date")
        arrival_date = self.request.query_params.get("arrival_date")
        airplane_id = self.request.query_params.get("airplane_id")

        if departure_date:
            queryset = queryset.filter(departure_time__date=departure_date)

        if arrival_date:
            queryset = queryset.filter(arrival_time__date=arrival_date)

        if airplane_id:
            airplane_id = airplane_id.split(",")
            queryset = queryset.filter(airplane__id__in=airplane_id)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer

        if self.action == "retrieve":
            return FlightDetailSerializer

        return FlightSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related(
        "tickets__flight__route", "tickets__flight__airplane"
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
