# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Metro Photos aims to gather pictures of all metro entrances in Paris and link them to their entrance, station, and lines. The project consists of:

1. **Data Pipeline** (`data/` folder): Python scripts that fetch and transform Paris metro data from IDFM (Île-de-France Mobilités) open datasets
2. **Web App** (`app/` folder): Planned website for viewing and uploading metro entrance photos (currently empty)

## Data Pipeline Architecture

The data pipeline transforms IDFM source files into a unified dataset that links metro stations, entrances, lines, and geographic coordinates.

### Data Flow

Source data (`data/source/`) → Transform script (`data/main.py`) → Generated data (`data/generated/`)

The transformation process:
1. Parses 4 source JSON files from IDFM APIs
2. Uses Pydantic models (`data/models.py`) to validate and normalize the data
3. Filters to metro-only stations (excludes RER, trains, etc.)
4. Joins zones (stations), accesses (entrances), and lines together
5. Outputs the final `zones_metro.json` with all metro stations including their entrances and line associations

### Key Models (data/models.py)

- **Zone**: A metro station with its location, town, and postal region
- **Access**: An entrance to a metro station with name and geographic coordinates (Lambert 93 and lat/lon)
- **Line**: A metro line with ID, name, and icon URL
- **ZoneAccessRelationship**: Links zones to their accesses
- **ZoneLineRelationship**: Links zones to their lines, includes mode filtering

### Running the Data Pipeline

```bash
cd data
uv run main.py
```

The `main.py` script uses the `uv --script` shebang, so it can also be run directly:

```bash
cd data
./main.py
```

This will:
- Clean existing generated files
- Transform each source file with Pydantic validation
- Combine all relationships into `zones_metro.json`

### Data Sources

All source data comes from https://data.iledefrance-mobilites.fr:
- `acces.json`: Metro entrance locations and names
- `zones-d-arrets.json`: Stop zones (stations) for all transit types
- `relations-acces.json`: Relationships between zones and accesses
- `emplacement-des-gares-idf.json`: Station locations with line information

The final output is `zones_metro.json` which contains only metro stations (filtered by `type == "metroStation"` and `mode == "METRO"`).

## Python Environment

- Python 3.12 (specified in `data/.python-version`)
- Dependencies managed with `uv` package manager
- Main dependency: Pydantic 2.12.5+ for data validation

## Front-End Web Application

Location: `app/front/`

Vue.js 3 application that displays Paris metro stations and entrances on an interactive OpenStreetMap.

### Architecture

- **Vue 3 + Vite**: Modern development setup with fast HMR
- **Leaflet**: Map rendering and interaction
- **proj4**: Coordinate transformation from Lambert 93 (EPSG:2154) to WGS84 (EPSG:4326)

### Key Components

- `src/components/MetroMap.vue`: Main map component displaying metro stations and entrances as markers
- `src/utils/coordinates.js`: Lambert 93 ↔ WGS84 coordinate conversion utilities
- `src/App.vue`: Root component with data loading and error handling
- `public/data/zones_metro.json`: Copied from data pipeline output

### Running the App

```bash
cd app/front
npm install
npm run dev
```

The app will be available at `http://localhost:5173`

### Data Updates

When the data pipeline generates new data, copy it to the front-end:

```bash
cp data/generated/zones_metro.json app/front/public/data/
```

### Map Features

- Each metro entrance is displayed as an orange circle marker
- Click any marker to see: station name, entrance name, metro lines, and town
- Map is centered on Paris with zoom controls
- Uses OpenStreetMap tiles

### Future Features

The planned enhancements include:
- Photo upload functionality with automatic entrance matching
- Photo display for each entrance/station
- Cloud object storage integration (e.g., OVH Object Storage)
- Face blurring for privacy (requires backend + background tasks)
