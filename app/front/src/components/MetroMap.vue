<template>
  <div ref="mapContainer" class="map-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, type Ref } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Zone, Access } from "../types/metro";
import { createTileLayer, createPieChartIcon, createEntranceIcon } from "@/utils/map";

interface Props {
  zones?: Zone[];
}

// Station-level data (one per zone)
interface StationData {
  zone: Zone;
  latLon: [number, number];
  lineColors: string[];
  marker: L.Marker | null;
}

// Entrance-level data (one per access)
interface EntranceData {
  zone: Zone;
  access: Access;
  latLon: [number, number];
  primaryColor: string;
  marker: L.Marker | null;
}

const props = withDefaults(defineProps<Props>(), {
  zones: () => [],
});

const emit = defineEmits<{
  "entrance-clicked": [accessId: string | null];
}>();

const mapContainer: Ref<HTMLElement | null> = ref(null);
const minZoom = 12;
const maxZoom = 19;

let map: L.Map | null = null;
let resizeObserver: ResizeObserver | null = null;
let stationsLayer: L.LayerGroup | null = null;
let entrancesLayer: L.LayerGroup | null = null;

// Which station is currently "open" (showing its entrances)
let openStationId: string | null = null;
let openPolylines: L.Polyline[] = [];
let openedTooltipMarker: L.Marker | null = null;

// All data
let allStations: StationData[] = [];
let allEntrances: EntranceData[] = [];

// RAF guard
let pendingVisibilityUpdate = false;

// --- Helpers ---

function getStationMarkerSize(): number {
  if (!map) return 12;
  return (6 + (map.getZoom() - minZoom) * 2.5) * 2;
}

function getEntranceMarkerSize(): number {
  return Math.round(getStationMarkerSize() * 0.65);
}

function computeStationCenter(zone: Zone): [number, number] {
  if (zone.accesses.length === 0) return [0, 0];
  let sumLat = 0;
  let sumLon = 0;
  for (const access of zone.accesses) {
    sumLat += access.geo_point.lat;
    sumLon += access.geo_point.lon;
  }
  return [sumLat / zone.accesses.length, sumLon / zone.accesses.length];
}

// --- Tooltip content ---

function stationTooltipContent(sd: StationData): string {
  const count = sd.zone.accesses.length;
  const entranceText = count === 1 ? "1 entrance" : `${count} entrances`;

  const lineIcons = sd.zone.lines
    .filter((l) => l.icon_url)
    .map((l) => `<img src="${l.icon_url}" alt="${l.name}" style="height: 16px;" />`)
    .join("");

  return `
    <div class="metro-tooltip">
      <strong>${sd.zone.name}</strong><br>
      <span style="font-size: 11px; color: #666;">${entranceText}</span>
      ${lineIcons ? `<div style="display: flex; gap: 2px; margin-top: 4px; flex-wrap: wrap;">${lineIcons}</div>` : ""}
    </div>
  `;
}

function entranceTooltipContent(ed: EntranceData): string {
  return `
    <div class="metro-tooltip">
      <strong>${ed.zone.name}</strong><br>
      ${ed.access.name}
    </div>
  `;
}

// --- Tooltip helpers ---

function closeOpenedTooltip(): void {
  if (openedTooltipMarker) {
    openedTooltipMarker.closeTooltip();
    openedTooltipMarker = null;
  }
}

// --- Station marker creation/destruction ---

function createStationMarker(sd: StationData, size: number, dimmed = false): L.Marker {
  const icon = createPieChartIcon(sd.lineColors, size, dimmed);
  const marker = L.marker(sd.latLon, { icon });

  marker.bindTooltip(stationTooltipContent(sd), {
    direction: "top",
    offset: [0, -size / 4],
    className: "custom-tooltip",
  });

  marker.on("click", (e) => {
    L.DomEvent.stopPropagation(e);
    if (openStationId === sd.zone.id) {
      closeStation();
    } else {
      openStation(sd);
    }
  });

  sd.marker = marker;
  return marker;
}

function destroyStationMarker(sd: StationData): void {
  if (!sd.marker) return;
  if (openedTooltipMarker === sd.marker) openedTooltipMarker = null;
  sd.marker.off("click");
  sd.marker.unbindTooltip();
  stationsLayer?.removeLayer(sd.marker);
  sd.marker = null;
}

// --- Entrance marker creation/destruction ---

function createEntranceMarker(ed: EntranceData, size: number): L.Marker {
  const icon = createEntranceIcon(ed.primaryColor, size);
  const marker = L.marker(ed.latLon, { icon });

  marker.bindTooltip(entranceTooltipContent(ed), {
    direction: "top",
    offset: [0, -size / 4],
    className: "custom-tooltip",
  });

  // Stop propagation so clicking an entrance doesn't close the station
  marker.on("click", (e) => {
    L.DomEvent.stopPropagation(e);
    emit("entrance-clicked", ed.access.id);
  });

  ed.marker = marker;
  return marker;
}

function destroyEntranceMarker(ed: EntranceData): void {
  if (!ed.marker) return;
  if (openedTooltipMarker === ed.marker) openedTooltipMarker = null;
  ed.marker.off("click");
  ed.marker.unbindTooltip();
  entrancesLayer?.removeLayer(ed.marker);
  ed.marker = null;
}

// --- Polyline helpers ---

function clearPolylines(): void {
  for (const pl of openPolylines) {
    entrancesLayer?.removeLayer(pl);
  }
  openPolylines = [];
}

// --- Open / Close station ---

function openStation(sd: StationData): void {
  if (!map || !entrancesLayer) return;

  // Close any currently open station first
  closeStation();

  openStationId = sd.zone.id;

  // Dim the station marker
  const stationSize = getStationMarkerSize();
  if (sd.marker) {
    sd.marker.setIcon(createPieChartIcon(sd.lineColors, stationSize, true));
  }

  // Show entrance markers + polylines for this station
  const entranceSize = getEntranceMarkerSize();
  const stationEntrances = allEntrances.filter((e) => e.zone.id === sd.zone.id);

  for (const ed of stationEntrances) {
    // Dotted line from station to entrance
    const pl = L.polyline([sd.latLon, ed.latLon], {
      color: "#999",
      weight: 1.5,
      dashArray: "4 6",
      interactive: false,
    });
    entrancesLayer.addLayer(pl);
    openPolylines.push(pl);

    // Entrance marker
    const marker = createEntranceMarker(ed, entranceSize);
    entrancesLayer.addLayer(marker);
  }

  // Zoom to fit entrances + station
  if (stationEntrances.length > 0) {
    const allPoints = [sd.latLon, ...stationEntrances.map((e) => e.latLon)];
    const bounds = L.latLngBounds(allPoints);
    map.flyToBounds(bounds, { padding: [80, 80], maxZoom: 18 });
  }
}

function closeStation(): void {
  if (!openStationId) return;

  emit("entrance-clicked", null);
  closeOpenedTooltip();
  clearPolylines();

  // Remove entrance markers for the open station
  for (const ed of allEntrances) {
    if (ed.zone.id === openStationId && ed.marker) {
      destroyEntranceMarker(ed);
    }
  }

  // Restore the station marker to non-dimmed
  const sd = allStations.find((s) => s.zone.id === openStationId);
  openStationId = null;

  if (sd?.marker) {
    const size = getStationMarkerSize();
    sd.marker.setIcon(createPieChartIcon(sd.lineColors, size, false));
  }
}

// --- Viewport-based station marker sync ---

function syncVisibleMarkers(): void {
  if (!map || !stationsLayer) return;

  const bounds = map.getBounds();
  const size = getStationMarkerSize();

  for (const sd of allStations) {
    const visible = bounds.contains(sd.latLon);
    const isOpen = sd.zone.id === openStationId;

    if (visible && !sd.marker) {
      const marker = createStationMarker(sd, size, isOpen);
      stationsLayer.addLayer(marker);
    } else if (!visible && sd.marker) {
      destroyStationMarker(sd);
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

// --- Build data (when zones change) ---

function buildMarkers(): void {
  if (!stationsLayer || !entrancesLayer) return;

  // Destroy all existing
  closeStation();
  for (const sd of allStations) destroyStationMarker(sd);
  for (const ed of allEntrances) destroyEntranceMarker(ed);
  stationsLayer.clearLayers();
  entrancesLayer.clearLayers();
  allStations = [];
  allEntrances = [];

  for (const zone of props.zones) {
    const lineColors = zone.lines.map((l) => l.color).filter((c) => c) as string[];
    const primaryColor = lineColors[0] ?? "#ff7800";

    // Station data
    allStations.push({
      zone,
      latLon: computeStationCenter(zone),
      lineColors,
      marker: null,
    });

    // Entrance data
    for (const access of zone.accesses) {
      allEntrances.push({
        zone,
        access,
        latLon: [access.geo_point.lat, access.geo_point.lon],
        primaryColor,
        marker: null,
      });
    }
  }

  syncVisibleMarkers();
}

// --- Zoom handler (resize icons) ---

function onZoomEnd(): void {
  if (!stationsLayer || !entrancesLayer) return;
  const stationSize = getStationMarkerSize();
  const entranceSize = getEntranceMarkerSize();

  for (const sd of allStations) {
    if (sd.marker && stationsLayer.hasLayer(sd.marker)) {
      const isOpen = sd.zone.id === openStationId;
      sd.marker.setIcon(createPieChartIcon(sd.lineColors, stationSize, isOpen));
    }
  }
  for (const ed of allEntrances) {
    if (ed.marker && entrancesLayer.hasLayer(ed.marker)) {
      ed.marker.setIcon(createEntranceIcon(ed.primaryColor, entranceSize));
    }
  }

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
  if (!map || !entrancesLayer) return;

  const found = allEntrances.find((e) => e.access.id === accessId);
  if (!found) return;

  const station = allStations.find((s) => s.zone.id === found.zone.id);
  if (!station) return;

  // Open the parent station (if not already open)
  if (openStationId !== found.zone.id) {
    closeStation();
    openStationId = found.zone.id;

    // Dim station marker
    const stationSize = getStationMarkerSize();
    if (station.marker) {
      station.marker.setIcon(createPieChartIcon(station.lineColors, stationSize, true));
    }

    // Show entrance markers + polylines
    const entranceSize = getEntranceMarkerSize();
    const stationEntrances = allEntrances.filter((e) => e.zone.id === found.zone.id);
    for (const ed of stationEntrances) {
      const pl = L.polyline([station.latLon, ed.latLon], {
        color: "#999",
        weight: 1.5,
        dashArray: "4 6",
        interactive: false,
      });
      entrancesLayer.addLayer(pl);
      openPolylines.push(pl);

      const marker = createEntranceMarker(ed, entranceSize);
      entrancesLayer.addLayer(marker);
    }
  }

  // Fly to the specific entrance
  map.flyTo(found.latLon, Math.max(map.getZoom(), 18));
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

  stationsLayer = L.layerGroup().addTo(map);
  entrancesLayer = L.layerGroup().addTo(map);

  if (props.zones.length > 0) {
    buildMarkers();
  }

  map.on("zoomend", onZoomEnd);
  map.on("moveend", updateVisibleMarkers);
  map.on("click", () => closeStation());

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
  clearPolylines();
  for (const sd of allStations) destroyStationMarker(sd);
  for (const ed of allEntrances) destroyEntranceMarker(ed);
  allStations = [];
  allEntrances = [];
  if (map) {
    map.remove();
    map = null;
  }
  stationsLayer = null;
  entrancesLayer = null;
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
/* Pie chart marker styles */
.pie-chart-marker {
  background: none !important;
  border: none !important;
  transition: opacity 0.3s ease;
}

/* Entrance marker styles */
.entrance-marker {
  background: none !important;
  border: none !important;
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
