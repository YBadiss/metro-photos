import proj4 from 'proj4'

// Define Lambert 93 (EPSG:2154) projection
proj4.defs('EPSG:2154', '+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs')

// Define WGS84 (EPSG:4326) - standard lat/lon used by OpenStreetMap
proj4.defs('EPSG:4326', '+proj=longlat +datum=WGS84 +no_defs')

/**
 * Convert Lambert 93 coordinates to WGS84 (lat/lon)
 * @param {number} x - Lambert 93 X coordinate
 * @param {number} y - Lambert 93 Y coordinate
 * @returns {[number, number]} [latitude, longitude]
 */
export function lambert93ToWGS84(x, y) {
  const [lon, lat] = proj4('EPSG:2154', 'EPSG:4326', [x, y])
  return [lat, lon]
}

/**
 * Convert WGS84 (lat/lon) to Lambert 93 coordinates
 * @param {number} lat - Latitude
 * @param {number} lon - Longitude
 * @returns {[number, number]} [x, y] in Lambert 93
 */
export function wgs84ToLambert93(lat, lon) {
  return proj4('EPSG:4326', 'EPSG:2154', [lon, lat])
}
