import csv
import time

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from apps.fuel.models import FuelStation
from apps.fuel.services.geocoder import geocode


class Command(BaseCommand):
    help = "Import fuel stations"

    def add_arguments(self, parser):
        parser.add_argument("csv_file")

    def handle(self, *args, **options):
        path = options["csv_file"]

        with open(path, newline="", encoding="utf-8") as csvfile:

            reader = csv.DictReader(csvfile)

            for row in reader:

                address = (
                    f'{row["Address"]}, '
                    f'{row["City"]}, '
                    f'{row["State"]}'
                )

                location = geocode(address)

                if location is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Cannot geocode {address}"
                        )
                    )
                    continue

                lat, lon = location

                FuelStation.objects.update_or_create(
                    opis_id=row["OPIS Truckstop ID"],
                    defaults={
                        "truckstop_name": row["Truckstop Name"],
                        "address": row["Address"],
                        "city": row["City"],
                        "state": row["State"],
                        "rack_id": row["Rack ID"] or None,
                        "retail_price": row["Retail Price"],
                        "location": Point(
                            lon,
                            lat,
                            srid=4326,
                        ),
                    },
                )

                self.stdout.write(
                    self.style.SUCCESS(address)
                )

                # Considering rate limit from openstreetmap
                time.sleep(2)