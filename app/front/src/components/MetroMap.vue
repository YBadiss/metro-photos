<template>
  <div ref="mapContainer" class="map-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, type Ref } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { lambert93ToWGS84 } from "../utils/coordinates";
import type { Zone, Access } from "../types/metro";

interface Props {
  zones?: Zone[];
}

interface MarkerData {
  marker: L.Marker | null;
  zone: Zone;
  access: Access;
  latLon: [number, number];
  lineColors: string[];
  lineNames: string;
}

const props = withDefaults(defineProps<Props>(), {
  zones: () => [],
});

const mapContainer: Ref<HTMLElement | null> = ref(null);
const minZoom = 12;
const maxZoom = 19;
let map: L.Map | null = null;
let resizeObserver: ResizeObserver | null = null;
let markersLayer: L.LayerGroup | null = null;

// Selection state
let selectedAccess: Access | null = null;
let selectedZone: Zone | null = null;
let pinpointMode = false;
let openedTooltipMarker: L.Marker | null = null;

// All entrance data (lightweight, markers created/destroyed on demand)
let allMarkers: MarkerData[] = [];

// --- Icon helpers ---

function getMarkerSize(): number {
  if (!map) return 12;
  return (6 + (map.getZoom() - minZoom) * 2.5) * 2;
}

function createPieChartIcon(colors: string[], size: number, dimmed = false): L.DivIcon {
  const radius = size / 2;
  const center = size / 2;

  if (!colors || colors.length === 0) {
    colors = ["#ff7800"];
  }

  let svgSegments = "";
  const opacity = dimmed ? 0.2 : 1;

  if (colors.length === 1) {
    svgSegments = `<circle cx="${center}" cy="${center}" r="${radius - 1}" fill="${colors[0]}" stroke="#000" stroke-width="1" opacity="${opacity}"/>`;
  } else {
    const anglePerSegment = 360 / colors.length;

    colors.forEach((color, index) => {
      const startAngle = index * anglePerSegment;
      const endAngle = (index + 1) * anglePerSegment;
      const startRad = ((startAngle - 90) * Math.PI) / 180;
      const endRad = ((endAngle - 90) * Math.PI) / 180;
      const x1 = center + (radius - 1) * Math.cos(startRad);
      const y1 = center + (radius - 1) * Math.sin(startRad);
      const x2 = center + (radius - 1) * Math.cos(endRad);
      const y2 = center + (radius - 1) * Math.sin(endRad);
      const largeArcFlag = anglePerSegment > 180 ? 1 : 0;
      const pathData = `M ${center},${center} L ${x1},${y1} A ${radius - 1},${radius - 1} 0 ${largeArcFlag},1 ${x2},${y2} Z`;
      svgSegments += `<path d="${pathData}" fill="${color}" stroke="#000" stroke-width="0.5" opacity="${opacity}"/>`;
    });

    svgSegments += `<circle cx="${center}" cy="${center}" r="${radius - 1}" fill="none" stroke="#000" stroke-width="1" opacity="${opacity}"/>`;
  }

  const svg = `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">${svgSegments}</svg>`;

  return L.divIcon({
    html: svg,
    className: "pie-chart-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// --- Selection logic ---

function isDimmed(md: MarkerData): boolean {
  if (!selectedAccess || !selectedZone) return false;

  if (pinpointMode) {
    return md.access.id !== selectedAccess.id;
  }

  // Line-sharing mode: highlight if same access or shares lines
  if (md.access.id === selectedAccess.id) return false;
  const selectedLineIds = selectedZone.lines.map((l) => l.id);
  return !md.zone.lines.some((l) => selectedLineIds.includes(l.id));
}

function applyIcons(): void {
  if (!markersLayer) return;
  const size = getMarkerSize();
  for (const md of allMarkers) {
    if (md.marker && markersLayer.hasLayer(md.marker)) {
      md.marker.setIcon(createPieChartIcon(md.lineColors, size, isDimmed(md)));
    }
  }
}

function closeOpenedTooltip(): void {
  if (openedTooltipMarker) {
    openedTooltipMarker.closeTooltip();
    openedTooltipMarker = null;
  }
}

function selectEntrance(access: Access, zone: Zone, pinpoint: boolean): void {
  closeOpenedTooltip();
  selectedAccess = access;
  selectedZone = zone;
  pinpointMode = pinpoint;
  applyIcons();
}

function resetSelection(): void {
  if (!selectedAccess) return;
  closeOpenedTooltip();
  selectedAccess = null;
  selectedZone = null;
  pinpointMode = false;
  applyIcons();
}

// --- On-demand marker creation/destruction ---

function createMarkerForData(md: MarkerData, size: number): L.Marker {
  const icon = createPieChartIcon(md.lineColors, size, isDimmed(md));
  const marker = L.marker(md.latLon, { icon });

  const tooltipContent = `
    <div class="metro-tooltip">
      <strong>${md.zone.name}</strong><br>
      ${md.access.name}<br>
      <span style="font-size: 11px; color: #666;">${md.lineNames || "N/A"}</span>
    </div>
  `;
  marker.bindTooltip(tooltipContent, {
    direction: "top",
    offset: [0, -size / 4],
    className: "custom-tooltip",
  });

  marker.on("click", (e) => {
    L.DomEvent.stopPropagation(e);
    if (selectedAccess?.id === md.access.id) {
      resetSelection();
    } else {
      selectEntrance(md.access, md.zone, false);
    }
  });

  md.marker = marker;
  return marker;
}

function destroyMarkerForData(md: MarkerData): void {
  if (!md.marker) return;
  if (openedTooltipMarker === md.marker) {
    openedTooltipMarker = null;
  }
  md.marker.off("click");
  md.marker.unbindTooltip();
  if (markersLayer) {
    markersLayer.removeLayer(md.marker);
  }
  md.marker = null;
}

// --- Viewport-based marker lifecycle ---

function updateVisibleMarkers(): void {
  if (!map || !markersLayer) return;

  const bounds = map.getBounds();
  const size = getMarkerSize();

  for (const md of allMarkers) {
    const visible = bounds.contains(md.latLon);
    if (visible && !md.marker) {
      const marker = createMarkerForData(md, size);
      markersLayer.addLayer(marker);
    } else if (!visible && md.marker) {
      destroyMarkerForData(md);
    }
  }
}

// --- Build entrance data (only when zones data changes) ---

function buildMarkers(): void {
  if (!markersLayer) return;

  // Destroy all existing markers
  for (const md of allMarkers) {
    destroyMarkerForData(md);
  }
  markersLayer.clearLayers();
  allMarkers = [];

  props.zones.forEach((zone) => {
    const lineColors = zone.lines.map((line) => line.color).filter((c) => c) as string[];
    const lineNames = zone.lines.map((line) => line.name).join(", ");

    zone.accesses.forEach((access) => {
      const latLon: [number, number] = lambert93ToWGS84(access.x_lambert_93, access.y_lambert_93);
      allMarkers.push({ marker: null, zone, access, latLon, lineColors, lineNames });
    });
  });

  updateVisibleMarkers();
}

// --- Zoom handler (resize icons only, no marker recreation) ---

function onZoomEnd(): void {
  applyIcons();
  updateVisibleMarkers();
}

// --- Public API ---

function invalidateSize(): void {
  if (map) {
    setTimeout(() => map?.invalidateSize(), 0);
    setTimeout(() => map?.invalidateSize(), 100);
    setTimeout(() => map?.invalidateSize(), 300);
  }
}

function flyToEntrance(accessId: string): void {
  if (!map || !markersLayer) return;

  const found = allMarkers.find((m) => m.access.id === accessId);
  if (!found) return;

  // Create marker if it doesn't exist yet (out of viewport)
  const size = getMarkerSize();
  if (!found.marker) {
    createMarkerForData(found, size);
  }
  if (!markersLayer.hasLayer(found.marker!)) {
    markersLayer.addLayer(found.marker!);
  }

  map.flyTo(found.latLon, 18);
  selectEntrance(found.access, found.zone, true);
  found.marker!.openTooltip();
  openedTooltipMarker = found.marker;
}

defineExpose({ invalidateSize, flyToEntrance });

// --- Lifecycle ---

onMounted(() => {
  if (!mapContainer.value) return;

  map = L.map(mapContainer.value, {
    minZoom,
    maxZoom,
  }).setView([48.8566, 2.3522], 12);

  L.tileLayer("https://api.maptiler.com/maps/streets-v4/{z}/{x}/{y}.png?key=PL2jHQqSB8xZ7Bp6aXpF", {
    attribution:
      '© <a href="https://www.maptiler.com/copyright/">MapTiler</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom,
  }).addTo(map);

  markersLayer = L.layerGroup().addTo(map);

  if (props.zones.length > 0) {
    buildMarkers();
  }

  map.on("zoomend", onZoomEnd);
  map.on("moveend", updateVisibleMarkers);
  map.on("click", resetSelection);

  resizeObserver = new ResizeObserver(() => {
    map?.invalidateSize();
  });
  resizeObserver.observe(mapContainer.value);
});

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});

watch(
  () => props.zones,
  () => {
    buildMarkers();
  },
);
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
