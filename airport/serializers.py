from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from airport.models import (
    Airport,
    Route,
    AirplaneType,
    Airplane,
    Crew,
    Flight,
    Ticket,
    Order,
)


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ["id", "name", "closest_big_city"]


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ["id", "source", "destination", "distance"]
        validators = [
            UniqueTogetherValidator(
                queryset=Route.objects.all(), fields=["source", "destination"]
            )
        ]

    def validate(self, attrs):
        Route.validate_route_location(
            attrs["source"],
            attrs["destination"],
            serializers.ValidationError,
        )
        return attrs


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="closest_big_city",
    )
    destination = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="closest_big_city",
    )


class RouteDetailSerializer(RouteSerializer):
    source = AirportSerializer(many=False, read_only=True)
    destination = AirportSerializer(many=False, read_only=True)


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ["id", "name"]


class AirplaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = ["id", "name", "rows", "seats_in_row", "capacity", "airplane_type"]

    def validate(self, attrs):
        Airplane.validate_airplane_size(
            attrs["rows"],
            attrs["seats_in_row"],
            serializers.ValidationError,
        )
        return attrs


class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="name",
    )


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ["id", "first_name", "last_name", "full_name"]


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = ["id", "route", "airplane", "crew", "departure_time", "arrival_time"]

    def validate(self, attrs):
        Flight.validate_flight_times(
            attrs["departure_time"],
            attrs["arrival_time"],
            serializers.ValidationError,
        )
        return attrs


class FlightListSerializer(serializers.ModelSerializer):
    route_source = serializers.CharField(
        source="route.source.closest_big_city",
        read_only=True,
    )
    route_destination = serializers.CharField(
        source="route.destination.closest_big_city",
        read_only=True,
    )
    airplane_name = serializers.CharField(source="airplane.name", read_only=True)
    airplane_capacity = serializers.IntegerField(
        source="airplane.capacity",
        read_only=True,
    )
    crew = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name",
    )

    class Meta:
        model = Flight
        fields = [
            "id",
            "route_source",
            "route_destination",
            "airplane_name",
            "airplane_capacity",
            "crew",
            "departure_time",
            "arrival_time",
        ]


class FlightDetailSerializer(FlightSerializer):
    route = RouteListSerializer(many=False, read_only=True)
    airplane = AirplaneListSerializer(many=False, read_only=True)
    crew = CrewSerializer(many=True, read_only=True)


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["id", "row", "seat", "flight"]
        validators = [
            UniqueTogetherValidator(
                queryset=Ticket.objects.all(),
                fields=["flight", "row", "seat"],
            )
        ]

    def validate(self, attrs):
        Ticket.validate_ticket(
            attrs["row"],
            attrs["flight"].airplane.rows,
            attrs["seat"],
            attrs["flight"].airplane.seats_in_row,
            serializers.ValidationError,
        )
        return attrs


class TicketListSerializer(TicketSerializer):
    flight = FlightListSerializer(many=False, read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ["id", "tickets", "created_at"]


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
