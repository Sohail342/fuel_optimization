from django.contrib.gis.db import models


class FuelStation(models.Model):
    opis_id = models.PositiveIntegerField(unique=True)

    truckstop_name = models.CharField(max_length=255)

    address = models.CharField(max_length=255)

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=2)

    rack_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    retail_price = models.DecimalField(
        max_digits=5,
        decimal_places=3,
    )

    # Longitude/Latitude
    location = models.PointField(
        geography=True,
        srid=4326,
        spatial_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["retail_price"]

        indexes = [
            models.Index(fields=["city", "state"]),
            models.Index(fields=["retail_price"]),
        ]

    def __str__(self):
        return f"{self.truckstop_name} ({self.city}, {self.state})"


class RouteCache(models.Model):
    start = models.CharField(max_length=255)

    destination = models.CharField(max_length=255)

    route = models.LineStringField(
        geography=True,
        srid=4326,
    )

    distance_miles = models.FloatField()

    duration_seconds = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["start", "destination"],
                name="unique_cached_route",
            )
        ]

    def __str__(self):
        return f"{self.start} → {self.destination}"
