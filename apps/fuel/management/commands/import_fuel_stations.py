import csv
import time
from decimal import Decimal, InvalidOperation

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
        imported = 0
        skipped = 0

        with open(path, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                row = {key.strip(): (value or "").strip() for key, value in row.items()}

                opis_id = row.get("OPIS Truckstop ID")
                retail_price_raw = row.get("Retail Price")
                address = f"{row.get('Address', '')}, {row.get('City', '')}, {row.get('State', '')}"

                if not opis_id:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping row with missing OPIS ID: {address}"
                        )
                    )
                    continue

                try:
                    retail_price = Decimal(retail_price_raw)
                except (InvalidOperation, TypeError):
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping row with invalid retail price: {address}"
                        )
                    )
                    continue

                rack_id_raw = row.get("Rack ID")
                rack_id = int(rack_id_raw) if rack_id_raw else None

                location = geocode(address)
                if location is None:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"Cannot geocode {address}"))
                    continue

                lat, lon = location
                FuelStation.objects.update_or_create(
                    opis_id=int(opis_id),
                    defaults={
                        "truckstop_name": row.get("Truckstop Name", ""),
                        "address": row.get("Address", ""),
                        "city": row.get("City", ""),
                        "state": row.get("State", ""),
                        "rack_id": rack_id,
                        "retail_price": retail_price,
                        "location": Point(lon, lat, srid=4326),
                    },
                )

                imported += 1
                self.stdout.write(self.style.SUCCESS(address))

                # Respect geocoder rate limits
                time.sleep(2)

        self.stdout.write(
            self.style.NOTICE(
                f"Import finished. Imported={imported}, skipped={skipped}"
            )
        )
