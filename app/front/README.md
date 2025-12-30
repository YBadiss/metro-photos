# Metro Photos - Front-End

Vue.js application for viewing Paris metro stations and entrances on an interactive map.

## Features

- Interactive OpenStreetMap showing all metro stations and entrances
- Automatic coordinate conversion from Lambert 93 to WGS84
- Click on any entrance marker to see:
  - Station name
  - Access/entrance name
  - Metro lines serving that station
  - Town/location

## Development

### Prerequisites

- Node.js (v16 or higher)
- npm

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Data

The app loads metro station data from `public/data/zones_metro.json`. This file is copied from `../../data/generated_data_files/zones_metro.json`.

To update the data:

1. Regenerate the data using the data pipeline:
   ```bash
   cd ../../data
   ./main.py
   ```

2. Copy the new file:
   ```bash
   cp ../../data/generated_data_files/zones_metro.json public/data/
   ```

## Project Structure

- `src/components/MetroMap.vue` - Main map component using Leaflet
- `src/utils/coordinates.js` - Coordinate conversion utilities (Lambert 93 ↔ WGS84)
- `src/App.vue` - Main application component with data loading
- `public/data/` - Static data files served by the app

## Technologies

- **Vue 3** - Progressive JavaScript framework
- **Vite** - Fast build tool and dev server
- **Leaflet** - Interactive maps library
- **proj4** - Coordinate transformation library
- **OpenStreetMap** - Map tiles provider
