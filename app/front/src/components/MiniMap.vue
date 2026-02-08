<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { GeoPoint, Zone } from "../types/metro";
import { createTileLayer, createPieChartIcon } from "@/utils/map";
import { haversineMeters } from "@/utils/coordinates";

const NEARBY_RADIUS_METERS = 150;
const MARKER_SIZE = 24;

const props = defineProps<{
  center: GeoPoint;
  zones: Zone[];
  matchedAccessId: string | null;
}>();

const emit = defineEmits<{
  "entrance-selected": [accessId: string];
}>();

const mapContainer = ref<HTMLElement | null>(null);
let map: L.Map | null = null;
let markersLayer: L.LayerGroup | null = null;
let photoDot: L.CircleMarker | null = null;

interface NearbyMarker {
  accessId: string;
  marker: L.Marker;
  colors: string[];
  name: string;
}
let nearbyMarkers: NearbyMarker[] = [];

function buildMarkers() {
  if (!map || !markersLayer) return;

  // Clear existing
  for (const nm of nearbyMarkers) {
    nm.marker.off("click");
    nm.marker.unbindTooltip();
    markersLayer.removeLayer(nm.marker);
  }
  nearbyMarkers = [];

  if (photoDot) {
    map.removeLayer(photoDot);
  }

  // Add photo location dot
  photoDot = L.circleMarker([props.center.lat, props.center.lon], {
    radius: 6,
    fillColor: "#3b82f6",
    fillOpacity: 0.9,
    color: "#1d4ed8",
    weight: 2,
    interactive: false,
  }).addTo(map);

  // Find nearby entrances
  for (const zone of props.zones) {
    const lineColors = zone.lines.map((l) => l.color).filter((c) => c) as string[];

    for (const access of zone.accesses) {
      const d = haversineMeters(
        props.center.lat,
        props.center.lon,
        access.geo_point.lat,
        access.geo_point.lon,
      );
      if (d > NEARBY_RADIUS_METERS) continue;

      const dimmed = access.id !== props.matchedAccessId;
      const icon = createPieChartIcon(lineColors, MARKER_SIZE, dimmed);
      const marker = L.marker([access.geo_point.lat, access.geo_point.lon], { icon });

      marker.bindTooltip(
        `<div class="metro-tooltip"><strong>${zone.name}</strong><br>${access.name}</div>`,
        { direction: "top", offset: [0, -MARKER_SIZE / 4], className: "custom-tooltip" },
      );

      marker.on("click", () => {
        emit("entrance-selected", access.id);
      });

      markersLayer.addLayer(marker);
      nearbyMarkers.push({ accessId: access.id, marker, colors: lineColors, name: access.name });
    }
  }
}

function updateMarkerStyles() {
  for (const nm of nearbyMarkers) {
    const dimmed = nm.accessId !== props.matchedAccessId;
    nm.marker.setIcon(createPieChartIcon(nm.colors, MARKER_SIZE, dimmed));
  }
}

watch(() => props.matchedAccessId, updateMarkerStyles);

watch(
  () => props.center,
  () => {
    if (map) {
      map.setView([props.center.lat, props.center.lon], 18);
      buildMarkers();
    }
  },
);

onMounted(() => {
  if (!mapContainer.value) return;

  map = L.map(mapContainer.value, {
    zoomControl: false,
    dragging: false,
    touchZoom: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false,
    keyboard: false,
    attributionControl: false,
  }).setView([props.center.lat, props.center.lon], 18);

  createTileLayer(19).addTo(map);
  markersLayer = L.layerGroup().addTo(map);

  buildMarkers();
});

onUnmounted(() => {
  for (const nm of nearbyMarkers) {
    nm.marker.off("click");
    nm.marker.unbindTooltip();
  }
  nearbyMarkers = [];
  if (map) {
    map.remove();
    map = null;
  }
  markersLayer = null;
});
</script>

<template>
  <div ref="mapContainer" class="w-full h-48 rounded-lg overflow-hidden"></div>
</template>
