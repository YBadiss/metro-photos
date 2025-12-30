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
let map = null
let markersLayer = null

onMounted(() => {
  // Initialize the map centered on Paris
  map = L.map(mapContainer.value).setView([48.8566, 2.3522], 12)

  // Add OpenStreetMap tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map)

  // Create a layer group for markers
  markersLayer = L.layerGroup().addTo(map)

  // Load initial markers if zones are already available
  if (props.zones.length > 0) {
    updateMarkers()
  }
})

// Watch for changes in zones data
watch(() => props.zones, () => {
  updateMarkers()
})

function updateMarkers() {
  if (!markersLayer) return

  // Clear existing markers
  markersLayer.clearLayers()

  // Add markers for each zone and its accesses
  props.zones.forEach(zone => {
    // Add markers for each access point
    zone.accesses.forEach(access => {
      const [lat, lon] = lambert93ToWGS84(access.x_lambert_93, access.y_lambert_93)

      // Create a marker for the access
      const marker = L.circleMarker([lat, lon], {
        radius: 6,
        fillColor: '#ff7800',
        color: '#000',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.8
      })

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
</style>
