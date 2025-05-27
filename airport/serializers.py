from django.db import transaction
from django.utils.timezone import now
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
    Country,
    City,
)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "country"]
        validators = [
            UniqueTogetherValidator(
                queryset=City.objects.all(), fields=["name", "country"]
            )
        ]


class CityListSerializer(CitySerializer):
    country = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="name",
    )


class CityNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["name"]


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ["id", "name", "country", "city", "closest_big_city", "image"]


class AirportListSerializer(AirportSerializer):
    city = CityNameSerializer(many=False, read_only=True)
    closest_big_city = CityNameSerializer(many=False, read_only=True)


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
    source = serializers.SerializerMethodField()
    destination = serializers.SerializerMethodField()

    def get_source(self, obj):
        return getattr(obj.source.closest_big_city, "name")

    def get_destination(self, obj):
        return getattr(obj.destination.closest_big_city, "name")


class RouteDetailSerializer(RouteSerializer):
    source = AirportListSerializer(many=False, read_only=True)
    destination = AirportListSerializer(many=False, read_only=True)


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ["id", "name"]


class AirplaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = [
            "id",
            "name",
            "rows",
            "seats_in_row",
            "capacity",
            "airplane_type",
            "airplane_image",
        ]

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
        fields = ["id", "first_name", "last_name", "full_name", "position", "image"]


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
        source="route.source.closest_big_city.name",
        read_only=True,
    )
    route_destination = serializers.CharField(
        source="route.destination.closest_big_city.name",
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
    tickets_available = serializers.IntegerField(read_only=True)

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
            "tickets_available",
        ]


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
        if attrs["flight"].departure_time <= now():
            raise serializers.ValidationError(
                "Cannot create ticket for a flight that has already departed."
            )

        Ticket.validate_ticket(
            attrs["row"],
            attrs["flight"].airplane.rows,
            attrs["seat"],
            attrs["flight"].airplane.seats_in_row,
            serializers.ValidationError,
        )
        return attrs


class TicketSeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["row", "seat"]


class FlightDetailSerializer(serializers.ModelSerializer):
    route = RouteListSerializer(many=False, read_only=True)
    airplane = AirplaneListSerializer(many=False, read_only=True)
    crew = CrewSerializer(many=True, read_only=True)
    taken_seats = TicketSeatSerializer(many=True, read_only=True, source="tickets")

    class Meta:
        model = Flight
        fields = [
            "id",
            "route",
            "airplane",
            "crew",
            "departure_time",
            "arrival_time",
            "duration",
            "taken_seats",
        ]


class TicketListSerializer(TicketSerializer):
    flight = FlightListSerializer(many=False, read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ["id", "tickets", "created_at"]

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(**ticket_data, order=order)
            return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
