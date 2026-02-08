<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ChevronLeft, Train, MapPin, Clock, Camera, Check } from "lucide-vue-next";
import type { Zone } from "../types/metro";
import type { FileUpload } from "../types/uploads";
import { haversineMeters } from "@/utils/coordinates";
import MiniMap from "./MiniMap.vue";

const API_URL = import.meta.env.VITE_API_URL || "";

const props = defineProps<{
  upload: FileUpload;
  zones: Zone[];
}>();

const emit = defineEmits<{
  close: [];
  validated: [photoId: number];
}>();

const validating = ref(false);

// Track the currently assigned access ID (user can reassign via mini map)
const currentAccessId = ref<string | null>(
  props.upload.result?.matchedEntrance?.entrance.id ?? null,
);

// When the upload prop changes (different photo selected), reset currentAccessId
watch(
  () => props.upload.id,
  () => {
    currentAccessId.value = props.upload.result?.matchedEntrance?.entrance.id ?? null;
  },
);

// Compute the current entrance info based on currentAccessId
const currentEntrance = computed(() => {
  if (!currentAccessId.value) return null;

  for (const zone of props.zones) {
    for (const access of zone.accesses) {
      if (access.id === currentAccessId.value) {
        return {
          entrance: { id: access.id, name: access.name, short_name: access.short_name },
          station: { id: zone.id, name: zone.name, town: zone.town },
          lines: zone.lines,
          distanceMeters: computeDistance(access.geo_point.lat, access.geo_point.lon),
        };
      }
    }
  }
  return null;
});

function computeDistance(accessLat: number, accessLon: number): number {
  const lat = props.upload.result?.exif?.latitude;
  const lon = props.upload.result?.exif?.longitude;
  if (lat == null || lon == null) return 0;
  return Math.round(haversineMeters(lat, lon, accessLat, accessLon));
}

const hasGps = computed(
  () => props.upload.result?.exif?.latitude != null && props.upload.result?.exif?.longitude != null,
);

const gpsCenter = computed(() => {
  if (!hasGps.value) return null;
  return {
    lat: props.upload.result!.exif!.latitude!,
    lon: props.upload.result!.exif!.longitude!,
  };
});

function formatCoord(lat: number, lon: number): string {
  const latDir = lat >= 0 ? "N" : "S";
  const lonDir = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(5)}° ${latDir}, ${Math.abs(lon).toFixed(5)}° ${lonDir}`;
}

function formatDateTime(date: string): string {
  return new Date(date).toLocaleString();
}

function onEntranceSelected(accessId: string) {
  currentAccessId.value = accessId;
}

async function validate() {
  const photoId = props.upload.photoId;
  if (!photoId || !currentAccessId.value) return;

  validating.value = true;
  try {
    const response = await fetch(`${API_URL}/photos/${photoId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "validated",
        accessId: currentAccessId.value,
      }),
    });

    if (!response.ok) {
      throw new Error("Validation failed");
    }

    emit("validated", photoId);
  } catch (err) {
    console.error("Failed to validate photo:", err);
  } finally {
    validating.value = false;
  }
}
</script>

<template>
  <div class="flex flex-col h-full border-l">
    <!-- Header -->
    <div class="flex items-center gap-2 px-3 py-3 border-b flex-shrink-0">
      <button class="p-1 hover:bg-muted rounded transition-colors" @click="emit('close')">
        <ChevronLeft class="w-4 h-4 text-muted-foreground" />
      </button>
      <h3 class="font-semibold text-sm truncate flex-1">{{ upload.file.name }}</h3>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto">
      <!-- Preview image -->
      <div class="border-b">
        <img
          :src="upload.result?.blurredUrl"
          :alt="upload.file.name"
          class="w-full object-contain max-h-40 bg-black/5"
        />
      </div>

      <div class="p-4 flex flex-col gap-4">
        <!-- Matched Metro Entrance -->
        <div v-if="currentEntrance" class="flex items-start gap-3">
          <Train class="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
          <div class="min-w-0">
            <p class="text-xs text-muted-foreground">Nearest Metro Entrance</p>
            <p class="font-medium">{{ currentEntrance.station.name }}</p>
            <p class="text-sm">{{ currentEntrance.entrance.name }}</p>
            <p class="text-xs text-muted-foreground mt-0.5">
              {{ currentEntrance.distanceMeters }}m away &middot;
              {{ currentEntrance.station.town }}
            </p>
            <div v-if="currentEntrance.lines.length" class="flex gap-1 mt-1.5">
              <img
                v-for="line in currentEntrance.lines"
                :key="line.id"
                :src="line.icon_url ?? ''"
                :alt="line.name"
                class="h-5"
              />
            </div>
          </div>
        </div>
        <div v-else class="flex items-center gap-3">
          <Train class="w-5 h-5 text-muted-foreground flex-shrink-0" />
          <p class="text-sm text-muted-foreground italic">No metro entrance nearby</p>
        </div>

        <!-- Mini Map -->
        <MiniMap
          v-if="gpsCenter"
          :center="gpsCenter"
          :zones="zones"
          :matched-access-id="currentAccessId"
          @entrance-selected="onEntranceSelected"
        />

        <!-- GPS Location -->
        <div v-if="hasGps" class="flex items-start gap-3">
          <MapPin class="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div>
            <p class="text-xs text-muted-foreground">Location</p>
            <p class="text-sm">
              {{ formatCoord(upload.result!.exif!.latitude!, upload.result!.exif!.longitude!) }}
            </p>
          </div>
        </div>
        <div v-else class="flex items-center gap-3">
          <MapPin class="w-5 h-5 text-muted-foreground flex-shrink-0" />
          <div>
            <p class="text-xs text-muted-foreground">Location</p>
            <p class="text-sm text-muted-foreground italic">No GPS data</p>
          </div>
        </div>

        <!-- Date/Time -->
        <div v-if="upload.result?.exif?.dateTime" class="flex items-start gap-3">
          <Clock class="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div>
            <p class="text-xs text-muted-foreground">Taken</p>
            <p class="text-sm">{{ formatDateTime(upload.result.exif.dateTime) }}</p>
          </div>
        </div>
        <div v-else class="flex items-center gap-3">
          <Clock class="w-5 h-5 text-muted-foreground flex-shrink-0" />
          <div>
            <p class="text-xs text-muted-foreground">Taken</p>
            <p class="text-sm text-muted-foreground italic">No date data</p>
          </div>
        </div>

        <!-- Camera -->
        <div v-if="upload.result?.exif?.camera" class="flex items-start gap-3">
          <Camera class="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div>
            <p class="text-xs text-muted-foreground">Camera</p>
            <p class="text-sm">{{ upload.result.exif.camera }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Validate button -->
    <div class="p-4 border-t flex-shrink-0">
      <button
        v-if="upload.status === 'validated'"
        class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-green-100 text-green-700 cursor-default"
        disabled
      >
        <Check class="w-4 h-4" />
        Validated
      </button>
      <button
        v-else
        class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        :class="
          upload.photoId && currentAccessId
            ? 'bg-primary text-primary-foreground hover:bg-primary/90'
            : 'bg-muted text-muted-foreground cursor-not-allowed'
        "
        :disabled="!upload.photoId || !currentAccessId || validating"
        @click="validate"
      >
        <Check class="w-4 h-4" />
        {{ validating ? "Validating..." : "Validate" }}
      </button>
    </div>
  </div>
</template>
