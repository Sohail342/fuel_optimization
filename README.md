# Fuel Assessment API

![Route Fuel Stop Cost flow](docs/Route%20Fuel%20Stop%20Cost.png)

This project is configured to run with Docker only. On Windows, a local non-Docker setup is not supported because the PostGIS/GeoDjango stack depends on native C++ build components that are not available in this environment.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose available through Docker Desktop
- A terminal with access to Docker

## Environment configuration

Create a file named `.env` in the project root with the following values:

```env
POSTGRES_DB=fuel_assessment
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgis
POSTGRES_PORT=5432
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
```

## Start the application with Docker

From the project root, run:

```bash
docker compose up --build
```

This will start:

- a PostGIS database container
- the Django API container

Once the containers are running, the API will be available at:

```text
http://localhost:8000
```

## Route planning API

Prefer **POST** with JSON so you can type spaces normally (no `%20`):

```bash
curl -X POST "http://localhost:8000/api/route-planning/" \
  -H "Content-Type: application/json" \
  -d "{\"start\": \"Houston, TX\", \"end\": \"Chicago, IL\"}"
```

Body:

```json
{
  "start": "Houston, TX",
  "end": "Chicago, IL"
}
```

`GET` still works for simple cases, but browsers/clients must URL-encode query strings. Swagger UI: `http://localhost:8000/api/docs/`

## Import fuel station data

The repository includes a CSV file that can be imported with the management command:

```bash
docker compose exec api python manage.py import_fuel_stations fuel-prices-for-be-assessment.csv
```

## Useful commands

Stop the containers:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f
```

## Notes

- The Docker setup uses PostgreSQL with PostGIS, so no local PostGIS installation is required.
- This project is intended for Docker-based development and testing only.
