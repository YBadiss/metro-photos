import proj4 from "proj4";

// Define Lambert 93 (EPSG:2154) projection
proj4.defs(
  "EPSG:2154",
  "+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs",
);

// Define WGS84 (EPSG:4326) - standard lat/lon used by OpenStreetMap
proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");

/**
 * Convert Lambert 93 coordinates to WGS84 (lat/lon)
 * @param x - Lambert 93 X coordinate
 * @param y - Lambert 93 Y coordinate
 * @returns [latitude, longitude]
 */
export function lambert93ToWGS84(x: number, y: number): [number, number] {
  const [lon, lat] = proj4("EPSG:2154", "EPSG:4326", [x, y]);
  return [lat, lon];
}

/**
 * Convert WGS84 (lat/lon) to Lambert 93 coordinates
 * @param lat - Latitude
 * @param lon - Longitude
 * @returns [x, y] in Lambert 93
 */
export function wgs84ToLambert93(lat: number, lon: number): [number, number] {
  return proj4("EPSG:4326", "EPSG:2154", [lon, lat]) as [number, number];
}

const toRad = (deg: number) => (deg * Math.PI) / 180;

/**
 * Calculate the distance in meters between two WGS84 points using the Haversine formula
 */
export function haversineMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}
