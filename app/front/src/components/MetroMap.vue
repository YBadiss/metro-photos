<template>
  <div ref="mapContainer" class="map-container"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { lambert93ToWGS84 } from '../utils/coordinates'

const props = defineProps({
  zones: {
    type: Array,
    default: () => []
  }
})

const mapContainer = ref(null)
const minZoom = 12
const maxZoom = 19
let map = null
let markersLayer = null

onMounted(() => {
  // Initialize the map centered on Paris with zoom constraints
  map = L.map(mapContainer.value, {
    minZoom,
    maxZoom
  }).setView([48.8566, 2.3522], 12)

  // Add MapTiler tiles
  L.tileLayer('https://api.maptiler.com/maps/streets-v4/{z}/{x}/{y}.png?key=PL2jHQqSB8xZ7Bp6aXpF', {
    attribution: '© <a href="https://www.maptiler.com/copyright/">MapTiler</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom
  }).addTo(map)

  // Create a layer group for markers
  markersLayer = L.layerGroup().addTo(map)

  // Load initial markers if zones are already available
  if (props.zones.length > 0) {
    updateMarkers()
  }

  // Update marker sizes when zoom level changes
  map.on('zoomend', updateMarkerSizes)
})

// Watch for changes in zones data
watch(() => props.zones, () => {
  updateMarkers()
})

function getRadiusForZoom(zoom) {
  return 6 + (zoom - minZoom) * 2.5
}

/**
 * Create a pie chart SVG icon for markers with multiple line colors
 * @param {Array} colors - Array of color strings for each line
 * @param {number} size - Diameter of the circle in pixels
 * @returns {L.DivIcon} Leaflet div icon with SVG pie chart
 */
function createPieChartIcon(colors, size) {
  const radius = size / 2
  const center = size / 2

  if (!colors || colors.length === 0) {
    // Fallback to orange if no colors
    colors = ['#ff7800']
  }

  let svgSegments = ''

  if (colors.length === 1) {
    // Single color - just a circle
    svgSegments = `<circle cx="${center}" cy="${center}" r="${radius - 1}" fill="${colors[0]}" stroke="#000" stroke-width="1"/>`
  } else {
    // Multiple colors - create pie slices
    const anglePerSegment = 360 / colors.length

    colors.forEach((color, index) => {
      const startAngle = index * anglePerSegment
      const endAngle = (index + 1) * anglePerSegment

      // Convert angles to radians
      const startRad = (startAngle - 90) * Math.PI / 180
      const endRad = (endAngle - 90) * Math.PI / 180

      // Calculate arc points
      const x1 = center + (radius - 1) * Math.cos(startRad)
      const y1 = center + (radius - 1) * Math.sin(startRad)
      const x2 = center + (radius - 1) * Math.cos(endRad)
      const y2 = center + (radius - 1) * Math.sin(endRad)

      // Create path for pie slice
      const largeArcFlag = anglePerSegment > 180 ? 1 : 0
      const pathData = `M ${center},${center} L ${x1},${y1} A ${radius - 1},${radius - 1} 0 ${largeArcFlag},1 ${x2},${y2} Z`

      svgSegments += `<path d="${pathData}" fill="${color}" stroke="#000" stroke-width="0.5"/>`
    })

    // Add border circle
    svgSegments += `<circle cx="${center}" cy="${center}" r="${radius - 1}" fill="none" stroke="#000" stroke-width="1"/>`
  }

  const svg = `
    <svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
      ${svgSegments}
    </svg>
  `

  return L.divIcon({
    html: svg,
    className: 'pie-chart-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  })
}

function updateMarkers() {
  if (!markersLayer) return

  // Clear existing markers
  markersLayer.clearLayers()

  const currentZoom = map.getZoom()
  const radius = getRadiusForZoom(currentZoom)
  const markerSize = radius * 2

  // Add markers for each zone and its accesses
  props.zones.forEach(zone => {
    // Get colors from the zone's lines (assuming each line has a 'color' field)
    const lineColors = zone.lines.map(line => line.color).filter(color => color)

    // Add markers for each access point
    zone.accesses.forEach(access => {
      const [lat, lon] = lambert93ToWGS84(access.x_lambert_93, access.y_lambert_93)

      // Create a marker with pie chart icon
      const icon = createPieChartIcon(lineColors, markerSize)
      const marker = L.marker([lat, lon], { icon })

      // Create popup content
      const lines = zone.lines.map(line => line.name).join(', ')
      const popupContent = `
        <div class="metro-popup">
          <h3>${zone.name}</h3>
          <p><strong>Access:</strong> ${access.name}</p>
          <p><strong>Lines:</strong> ${lines || 'N/A'}</p>
          <p><strong>Town:</strong> ${zone.town}</p>
        </div>
      `

      marker.bindPopup(popupContent)
      markersLayer.addLayer(marker)
    })
  })
}

function updateMarkerSizes() {
  // Redraw markers with new sizes when zoom changes
  updateMarkers()
}
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 100vh;
}
</style>

<style>
/* Global styles for popups */
.metro-popup h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #333;
}

.metro-popup p {
  margin: 5px 0;
  font-size: 14px;
}

.metro-popup strong {
  font-weight: 600;
}

/* Pie chart marker styles */
.pie-chart-marker {
  background: none !important;
  border: none !important;
}
</style>
