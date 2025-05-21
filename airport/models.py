from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Airport(models.Model):
    name = models.CharField(max_length=100, unique=True)
    closest_big_city = models.CharField(max_length=64)

    def __str__(self) -> str:
        return self.name


class Route(models.Model):
    source = models.ForeignKey(
        "Airport",
        on_delete=models.CASCADE,
        related_name="source_routes",
    )
    destination = models.ForeignKey(
        "Airport",
        on_delete=models.CASCADE,
        related_name="destination_routes",
    )
    distance = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "destination"], name="unique_route_source_destination"
            )
        ]

    def __str__(self) -> str:
        return f"{self.source.name} - {self.destination.name}"

    @staticmethod
    def validate_route_location(source, destination, error_to_raise):
        if source == destination:
            raise error_to_raise("Source and destination airports must be different")

    def clean(self):
        self.validate_route_location(self.source, self.destination, ValidationError)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AirplaneType(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self) -> str:
        return self.name


class Airplane(models.Model):
    name = models.CharField(max_length=64)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()
    airplane_type = models.ForeignKey(
        "AirplaneType",
        on_delete=models.CASCADE,
        related_name="airplanes",
    )

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_in_row

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def validate_airplane_size(rows, seats_in_row, error_to_raise):
        if rows <= 0:
            raise error_to_raise("Number of rows must be positive.")

        if seats_in_row <= 0:
            raise error_to_raise("Number of seats in a row must be positive.")

    def clean(self):
        self.validate_airplane_size(self.rows, self.seats_in_row, ValidationError)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Crew(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return self.first_name + " " + self.last_name


class Flight(models.Model):
    route = models.ForeignKey(
        "Route",
        on_delete=models.CASCADE,
        related_name="flights",
    )
    airplane = models.ForeignKey(
        "Airplane",
        on_delete=models.CASCADE,
        related_name="flights",
    )
    crew = models.ManyToManyField(
        Crew,
        related_name="flights",
        blank=True,
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    class Meta:
        ordering = ["-departure_time"]

    def __str__(self) -> str:
        return f"Flight: {self.id} on {str(self.route)}"

    @staticmethod
    def validate_flight_times(departure_time, arrival_time, error_to_raise):
        if departure_time >= arrival_time:
            raise error_to_raise("Arrival time must be after departure time")

    def clean(self):
        self.validate_flight_times(
            self.departure_time, self.arrival_time, ValidationError
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    flight = models.ForeignKey(
        "Flight",
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["flight", "row", "seat"], name="unique_ticket_row_seat_flight"
            )
        ]
        ordering = ["row", "seat"]

    def __str__(self) -> str:
        return (
            f"Ticket {self.id} for Flight {self.flight}, seat: {self.row} - {self.seat}"
        )

    @staticmethod
    def validate_ticket(row, num_rows, seat, num_seats, error_to_raise):
        if not (1 <= row <= num_rows):
            raise error_to_raise(
                {"row": f"row must be in range [1, {num_rows}], not {row}"}
            )

        if not (1 <= seat <= num_seats):
            raise error_to_raise(
                {"seat": f"seat must be in range [1, {num_seats}], not {seat}"}
            )

    def clean(self):
        self.validate_ticket(
            self.row,
            self.flight.airplane.rows,
            self.seat,
            self.flight.airplane.seats_in_row,
            ValidationError,
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order {self.id} by {self.user}"
