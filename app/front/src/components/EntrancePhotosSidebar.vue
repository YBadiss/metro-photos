<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { X, ImageOff, Loader2, ZoomIn } from "lucide-vue-next";
import type { Zone } from "../types/metro";
import PhotoLightbox from "./PhotoLightbox.vue";

const API_URL = import.meta.env.VITE_API_URL || "";

interface StationPhoto {
  id: number;
  thumbnail: string | null;
  accessId: string | null;
  latitude: number | null;
  longitude: number | null;
  takenAt: string | null;
  camera: string | null;
  createdAt: string;
}

interface DateGroup {
  label: string;
  sortKey: string;
  photos: StationPhoto[];
}

interface EntranceGroup {
  accessId: string;
  entranceName: string;
  dateGroups: DateGroup[];
}

const props = defineProps<{
  zoneId: string;
  filteredAccessId: string | null;
  zones: Zone[];
}>();

const emit = defineEmits<{
  close: [];
}>();

const allPhotos = ref<StationPhoto[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const lightboxPhotoId = ref<number | null>(null);

const stationInfo = computed(() => {
  const zone = props.zones.find((z) => z.id === props.zoneId);
  if (!zone) return null;
  return { name: zone.name, town: zone.town, lines: zone.lines, accesses: zone.accesses };
});

const entranceRefs = ref<Record<string, HTMLElement | null>>({});

function setEntranceRef(accessId: string, el: unknown) {
  entranceRefs.value[accessId] = el as HTMLElement | null;
}

function formatDateKey(dateStr: string): { label: string; sortKey: string } {
  const d = new Date(dateStr);
  const label = d.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
  // sortKey: ISO date for sorting (descending)
  const sortKey = d.toISOString().slice(0, 10);
  return { label, sortKey };
}

const entranceGroups = computed<EntranceGroup[]>(() => {
  if (!stationInfo.value) return [];

  // Group photos by accessId
  const byAccess = new Map<string, StationPhoto[]>();
  for (const photo of allPhotos.value) {
    const key = photo.accessId ?? "__unknown__";
    if (!byAccess.has(key)) byAccess.set(key, []);
    byAccess.get(key)!.push(photo);
  }

  // Build a group for every entrance in the station, even those with no photos
  const groups: EntranceGroup[] = stationInfo.value.accesses.map((access) => {
    const accessPhotos = byAccess.get(access.id) ?? [];

    // Group by day
    const byDate = new Map<string, { label: string; sortKey: string; photos: StationPhoto[] }>();
    for (const photo of accessPhotos) {
      const { label, sortKey } = photo.takenAt
        ? formatDateKey(photo.takenAt)
        : { label: "Date inconnue", sortKey: "0000-00-00" };
      if (!byDate.has(sortKey)) byDate.set(sortKey, { label, sortKey, photos: [] });
      byDate.get(sortKey)!.photos.push(photo);
    }

    const dateGroups = Array.from(byDate.values()).sort((a, b) => b.sortKey.localeCompare(a.sortKey));
    return { accessId: access.id, entranceName: access.name, dateGroups };
  });

  groups.sort((a, b) => a.entranceName.localeCompare(b.entranceName));
  return groups;
});

async function fetchPhotos(zoneId: string) {
  loading.value = true;
  error.value = null;
  allPhotos.value = [];

  try {
    const response = await fetch(`${API_URL}/zones/${zoneId}/photos`);
    if (!response.ok) {
      throw new Error(`Failed to fetch photos: ${response.statusText}`);
    }
    allPhotos.value = await response.json();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load photos";
    console.error("Error fetching station photos:", e);
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.zoneId,
  (id) => fetchPhotos(id),
  { immediate: true },
);

// Scroll to entrance section when an entrance is clicked on the map
watch(
  () => props.filteredAccessId,
  (accessId) => {
    if (!accessId) return;
    nextTick(() => {
      const el = entranceRefs.value[accessId];
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  },
);
</script>

<template>
  <div class="sidebar-root flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center gap-2 px-3 py-3 border-b flex-shrink-0">
      <div class="flex-1 min-w-0">
        <h3 v-if="stationInfo" class="font-semibold text-sm truncate">
          {{ stationInfo.name }}
        </h3>
        <p v-if="stationInfo" class="text-xs text-muted-foreground">
          {{ stationInfo.accesses.length }} entrée{{ stationInfo.accesses.length > 1 ? "s" : "" }}
        </p>
      </div>
      <button class="p-1 hover:bg-muted rounded transition-colors flex-shrink-0" @click="emit('close')">
        <X class="w-4 h-4 text-muted-foreground" />
      </button>
    </div>

    <!-- Line icons -->
    <div v-if="stationInfo?.lines.length" class="flex gap-1 px-3 py-2 border-b flex-shrink-0">
      <img
        v-for="line in stationInfo.lines"
        :key="line.id"
        :src="line.icon_url ?? ''"
        :alt="line.name"
        class="h-5"
      />
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 class="w-5 h-5 animate-spin" />
        <span class="ml-2 text-sm">Chargement des photos...</span>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="px-4 py-8 text-center">
        <p class="text-sm text-destructive">{{ error }}</p>
      </div>

      <!-- Entrance groups (always shown, even without photos) -->
      <div v-else class="pb-2">
        <div
          v-for="group in entranceGroups"
          :key="group.accessId"
          :ref="(el) => setEntranceRef(group.accessId, el)"
          class="entrance-group"
        >
          <!-- Entrance heading -->
          <div class="px-3 py-2 bg-muted/50 border-b">
            <p class="text-xs font-medium text-foreground truncate">{{ group.entranceName }}</p>
          </div>

          <!-- No photos for this entrance -->
          <div v-if="group.dateGroups.length === 0" class="flex items-center gap-2 px-3 py-3 text-muted-foreground">
            <ImageOff class="w-4 h-4 flex-shrink-0" />
            <p class="text-xs">Aucune photo</p>
          </div>

          <!-- Date groups -->
          <div v-for="dateGroup in group.dateGroups" :key="dateGroup.sortKey">
            <p class="px-3 py-1.5 text-xs text-muted-foreground">{{ dateGroup.label }}</p>
            <div class="photo-grid">
              <div
                v-for="photo in dateGroup.photos"
                :key="photo.id"
                class="photo-thumb aspect-square overflow-hidden rounded bg-muted relative cursor-pointer"
                @click="lightboxPhotoId = photo.id"
              >
                <img
                  v-if="photo.thumbnail"
                  :src="`data:image/jpeg;base64,${photo.thumbnail}`"
                  :alt="`Photo ${photo.id}`"
                  class="w-full h-full object-cover"
                />
                <div class="photo-thumb-overlay">
                  <ZoomIn class="w-5 h-5 text-white" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <PhotoLightbox
      v-if="lightboxPhotoId"
      :photo-id="lightboxPhotoId"
      @close="lightboxPhotoId = null"
    />
  </div>
</template>

<style scoped>
.sidebar-root {
  border-left: 1px solid hsl(var(--border));
}

.entrance-group + .entrance-group {
  border-top: 1px solid hsl(var(--border));
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.25rem;
  padding: 0 0.5rem 0.5rem;
}

.photo-thumb-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.photo-thumb:hover .photo-thumb-overlay {
  opacity: 1;
}

@media (max-width: 640px) {
  .sidebar-root {
    border-left: none;
    border-top: 1px solid hsl(var(--border));
  }

  .photo-grid {
    display: flex;
    overflow-x: auto;
    flex-wrap: nowrap;
    gap: 0.25rem;
    padding: 0 0.5rem 0.5rem;
  }

  .photo-grid .photo-thumb {
    width: 6rem;
    height: 6rem;
    flex-shrink: 0;
    aspect-ratio: auto;
  }
}
</style>
