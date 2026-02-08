<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { X, ImageOff, Loader2, ZoomIn } from "lucide-vue-next";
import type { Zone } from "../types/metro";
import PhotoLightbox from "./PhotoLightbox.vue";

const API_URL = import.meta.env.VITE_API_URL || "";

interface EntrancePhoto {
  id: number;
  thumbnail: string | null;
  latitude: number | null;
  longitude: number | null;
  takenAt: string | null;
  camera: string | null;
}

const props = defineProps<{
  accessId: string;
  zones: Zone[];
}>();

const emit = defineEmits<{
  close: [];
}>();

const photos = ref<EntrancePhoto[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const lightboxPhotoId = ref<number | null>(null);

const entranceInfo = computed(() => {
  for (const zone of props.zones) {
    for (const access of zone.accesses) {
      if (access.id === props.accessId) {
        return {
          entrance: { id: access.id, name: access.name },
          station: { name: zone.name, town: zone.town },
          lines: zone.lines,
        };
      }
    }
  }
  return null;
});

async function fetchPhotos(accessId: string) {
  loading.value = true;
  error.value = null;
  photos.value = [];

  try {
    const response = await fetch(`${API_URL}/accesses/${accessId}/photos`);
    if (!response.ok) {
      throw new Error(`Failed to fetch photos: ${response.statusText}`);
    }
    photos.value = await response.json();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load photos";
    console.error("Error fetching entrance photos:", e);
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.accessId,
  (id) => fetchPhotos(id),
  { immediate: true },
);
</script>

<template>
  <div class="flex flex-col h-full border-l">
    <!-- Header -->
    <div class="flex items-center gap-2 px-3 py-3 border-b flex-shrink-0">
      <div class="flex-1 min-w-0">
        <h3 v-if="entranceInfo" class="font-semibold text-sm truncate">
          {{ entranceInfo.station.name }}
        </h3>
        <p v-if="entranceInfo" class="text-xs text-muted-foreground truncate">
          {{ entranceInfo.entrance.name }}
        </p>
      </div>
      <button class="p-1 hover:bg-muted rounded transition-colors flex-shrink-0" @click="emit('close')">
        <X class="w-4 h-4 text-muted-foreground" />
      </button>
    </div>

    <!-- Line icons -->
    <div v-if="entranceInfo?.lines.length" class="flex gap-1 px-3 py-2 border-b flex-shrink-0">
      <img
        v-for="line in entranceInfo.lines"
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

      <!-- Empty state -->
      <div v-else-if="photos.length === 0" class="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <ImageOff class="w-8 h-8 mb-2" />
        <p class="text-sm">Aucune photo</p>
      </div>

      <!-- Photo grid -->
      <div v-else class="grid grid-cols-2 gap-1 p-2">
        <div
          v-for="photo in photos"
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

    <PhotoLightbox
      v-if="lightboxPhotoId"
      :photo-id="lightboxPhotoId"
      @close="lightboxPhotoId = null"
    />
  </div>
</template>

<style scoped>
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
</style>
