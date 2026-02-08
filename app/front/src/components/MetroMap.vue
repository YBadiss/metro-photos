<template>
  <div ref="mapContainer" class="map-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, type Ref } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Zone, Access } from "../types/metro";
import { createTileLayer, createPieChartIcon } from "@/utils/map";

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

// Protect a marker from being destroyed by updateVisibleMarkers during flyTo animation
let protectedAccessId: string | null = null;

// RAF guard for updateVisibleMarkers
let pendingVisibilityUpdate = false;

// --- Icon helpers ---

function getMarkerSize(): number {
  if (!map) return 12;
  return (6 + (map.getZoom() - minZoom) * 2.5) * 2;
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

function syncVisibleMarkers(): void {
  if (!map || !markersLayer) return;

  const bounds = map.getBounds();
  const size = getMarkerSize();

  for (const md of allMarkers) {
    const visible = bounds.contains(md.latLon);
    if (visible && !md.marker) {
      const marker = createMarkerForData(md, size);
      markersLayer.addLayer(marker);
    } else if (!visible && md.marker && md.access.id !== protectedAccessId) {
      destroyMarkerForData(md);
    }
  }
}

function updateVisibleMarkers(): void {
  if (pendingVisibilityUpdate) return;
  pendingVisibilityUpdate = true;
  requestAnimationFrame(() => {
    pendingVisibilityUpdate = false;
    syncVisibleMarkers();
  });
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
      const latLon: [number, number] = [access.geo_point.lat, access.geo_point.lon];
      allMarkers.push({ marker: null, zone, access, latLon, lineColors, lineNames });
    });
  });

  syncVisibleMarkers();
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

  // Protect the target marker from being destroyed during fly animation
  protectedAccessId = accessId;
  map.once("moveend", () => {
    protectedAccessId = null;
  });

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

  createTileLayer(maxZoom).addTo(map);

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
    resizeObserver = null;
  }
  for (const md of allMarkers) {
    destroyMarkerForData(md);
  }
  allMarkers = [];
  if (map) {
    map.remove();
    map = null;
  }
  markersLayer = null;
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
