<template>
  <div ref="mapContainer" class="map-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, type Ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { lambert93ToWGS84 } from '../utils/coordinates'
import type { Zone, Access } from '../types/metro'

interface Props {
  zones?: Zone[]
}

interface MarkerData {
  marker: L.Marker
  zone: Zone
  access: Access
}

const props = withDefaults(defineProps<Props>(), {
  zones: () => [],
})

const mapContainer: Ref<HTMLElement | null> = ref(null)
const minZoom = 12
const maxZoom = 19
let map: L.Map | null = null
let markersLayer: L.LayerGroup | null = null
let selectedAccess: Access | null = null
let selectedZone: Zone | null = null
let allMarkers: MarkerData[] = [] // Store all markers with their metadata

onMounted(() => {
  if (!mapContainer.value) return

  // Initialize the map centered on Paris with zoom constraints
  map = L.map(mapContainer.value, {
    minZoom,
    maxZoom,
  }).setView([48.8566, 2.3522], 12)

  // Add MapTiler tiles
  L.tileLayer('https://api.maptiler.com/maps/streets-v4/{z}/{x}/{y}.png?key=PL2jHQqSB8xZ7Bp6aXpF', {
    attribution:
      '© <a href="https://www.maptiler.com/copyright/">MapTiler</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom,
  }).addTo(map)

  // Create a layer group for markers
  markersLayer = L.layerGroup().addTo(map)

  // Load initial markers if zones are already available
  if (props.zones.length > 0) {
    updateMarkers()
  }

  // Update marker sizes when zoom level changes
  map.on('zoomend', updateMarkers)

  // Click anywhere on the map to reset selection
  map.on('click', resetSelection)
})

// Watch for changes in zones data
watch(
  () => props.zones,
  () => {
    updateMarkers()
  }
)

function getRadiusForZoom(zoom: number): number {
  return 6 + (zoom - minZoom) * 2.5
}

/**
 * Create a pie chart SVG icon for markers with multiple line colors
 * @param colors - Array of color strings for each line
 * @param size - Diameter of the circle in pixels
 * @param dimmed - Whether to dim the marker
 * @returns Leaflet div icon with SVG pie chart
 */
function createPieChartIcon(colors: string[], size: number, dimmed = false): L.DivIcon {
  const radius = size / 2
  const center = size / 2

  if (!colors || colors.length === 0) {
    // Fallback to orange if no colors
    colors = ['#ff7800']
  }

  let svgSegments = ''
  const opacity = dimmed ? 0.2 : 1

  if (colors.length === 1) {
    // Single color - just a circle
    svgSegments = `<circle cx="${center}" cy="${center}" r="${radius - 1}" fill="${colors[0]}" stroke="#000" stroke-width="1" opacity="${opacity}"/>`
  } else {
    // Multiple colors - create pie slices
    const anglePerSegment = 360 / colors.length

    colors.forEach((color, index) => {
      const startAngle = index * anglePerSegment
      const endAngle = (index + 1) * anglePerSegment

      // Convert angles to radians
      const startRad = ((startAngle - 90) * Math.PI) / 180
      const endRad = ((endAngle - 90) * Math.PI) / 180

      // Calculate arc points
      const x1 = center + (radius - 1) * Math.cos(startRad)
      const y1 = center + (radius - 1) * Math.sin(startRad)
      const x2 = center + (radius - 1) * Math.cos(endRad)
      const y2 = center + (radius - 1) * Math.sin(endRad)

      // Create path for pie slice
      const largeArcFlag = anglePerSegment > 180 ? 1 : 0
      const pathData = `M ${center},${center} L ${x1},${y1} A ${radius - 1},${radius - 1} 0 ${largeArcFlag},1 ${x2},${y2} Z`

      svgSegments += `<path d="${pathData}" fill="${color}" stroke="#000" stroke-width="0.5" opacity="${opacity}"/>`
    })

    // Add border circle
    svgSegments += `<circle cx="${center}" cy="${center}" r="${radius - 1}" fill="none" stroke="#000" stroke-width="1" opacity="${opacity}"/>`
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
    iconAnchor: [size / 2, size / 2],
  })
}

/**
 * Check if two accesses share any metro lines
 */
function shareLines(zone1: Zone, zone2: Zone): boolean {
  const lines1 = zone1.lines.map((l) => l.id)
  const lines2 = zone2.lines.map((l) => l.id)
  return lines1.some((id) => lines2.includes(id))
}

/**
 * Reset selection and show all markers normally
 */
function resetSelection(): void {
  if (selectedAccess === null) return

  selectedAccess = null
  selectedZone = null

  if (!map) return

  const currentZoom = map.getZoom()
  const radius = getRadiusForZoom(currentZoom)
  const markerSize = radius * 2

  allMarkers.forEach(({ marker, zone }) => {
    const lineColors = zone.lines.map((line) => line.color).filter((color) => color) as string[]
    const icon = createPieChartIcon(lineColors, markerSize, false)
    marker.setIcon(icon)
  })
}

/**
 * Handle marker click - highlight related accesses
 */
function onMarkerClick(clickedMarkerData: MarkerData, event: L.LeafletMouseEvent): void {
  // Prevent the map click event from firing
  L.DomEvent.stopPropagation(event)

  const { zone: clickedZone, access: clickedAccess } = clickedMarkerData

  // If clicking the same access again, reset
  if (selectedAccess && selectedAccess.id === clickedAccess.id) {
    resetSelection()
    return
  }
  onMarkerSelect(clickedAccess, clickedZone)
}

function onMarkerSelect(access: Access, zone: Zone): void {
  selectedAccess = access
  selectedZone = zone

  if (!map) return

  // Update all markers
  const currentZoom = map.getZoom()
  const radius = getRadiusForZoom(currentZoom)
  const markerSize = radius * 2

  allMarkers.forEach(({ marker, zone: markerZone, access: markerAccess }) => {
    const lineColors = markerZone.lines
      .map((line) => line.color)
      .filter((color) => color) as string[]

    // Check if this access shares lines with the clicked one
    const isRelated = shareLines(markerZone, zone) || markerAccess.id === access.id

    // Update icon with dimming
    const icon = createPieChartIcon(lineColors, markerSize, !isRelated)
    marker.setIcon(icon)
  })
}

function updateMarkers(): void {
  if (!markersLayer || !map) return

  // Clear existing markers
  markersLayer.clearLayers()
  allMarkers = []

  const currentZoom = map.getZoom()
  const radius = getRadiusForZoom(currentZoom)
  const markerSize = radius * 2

  // Add markers for each zone and its accesses
  props.zones.forEach((zone) => {
    // Get colors from the zone's lines
    const lineColors = zone.lines.map((line) => line.color).filter((color) => color) as string[]

    // Add markers for each access point
    zone.accesses.forEach((access) => {
      const [lat, lon] = lambert93ToWGS84(access.x_lambert_93, access.y_lambert_93)

      // Create a marker with pie chart icon
      const icon = createPieChartIcon(lineColors, markerSize)
      const marker = L.marker([lat, lon], { icon })

      // Create tooltip for hover
      const lines = zone.lines.map((line) => line.name).join(', ')
      const tooltipContent = `
        <div class="metro-tooltip">
          <strong>${zone.name}</strong><br>
          ${access.name}<br>
          <span style="font-size: 11px; color: #666;">${lines || 'N/A'}</span>
        </div>
      `
      marker.bindTooltip(tooltipContent, {
        direction: 'top',
        offset: [0, -radius],
        className: 'custom-tooltip',
      })

      // Store marker data for click interactions
      const markerData = { marker, zone, access }
      allMarkers.push(markerData)

      // Add click handler
      marker.on('click', (e) => onMarkerClick(markerData, e))

      if (markersLayer) {
        markersLayer.addLayer(marker)
      }
    })
  })

  if (selectedAccess && selectedZone) {
    onMarkerSelect(selectedAccess, selectedZone)
  }
}
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
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
  transition: opacity 0.3s ease;
}

/* Tooltip styles */
.metro-tooltip {
  font-size: 13px;
  line-height: 1.4;
  padding: 2px 0;
}

.metro-tooltip strong {
  font-weight: 600;
  color: #333;
}
</style>
