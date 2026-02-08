<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Loader2, ImageOff, ZoomIn } from "lucide-vue-next";
import type { Zone } from "../types/metro";
import PhotoLightbox from "./PhotoLightbox.vue";

const API_URL = import.meta.env.VITE_API_URL || "";

interface LatestPhoto {
  id: number;
  thumbnail: string | null;
  accessId: string | null;
  latitude: number | null;
  longitude: number | null;
  takenAt: string | null;
  camera: string | null;
  createdAt: string;
}

const props = defineProps<{
  zones: Zone[];
}>();

const photos = ref<LatestPhoto[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const lightboxPhotoId = ref<number | null>(null);

function lookupEntrance(accessId: string | null) {
  if (!accessId) return null;
  for (const zone of props.zones) {
    for (const access of zone.accesses) {
      if (access.id === accessId) {
        return { stationName: zone.name, entranceName: access.name, lines: zone.lines };
      }
    }
  }
  return null;
}

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("fr-FR", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

async function fetchLatest() {
  loading.value = true;
  error.value = null;
  try {
    const response = await fetch(`${API_URL}/photos/latest?limit=10`);
    if (!response.ok) throw new Error(`Failed to fetch: ${response.statusText}`);
    photos.value = await response.json();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load photos";
    console.error("Error fetching latest photos:", e);
  } finally {
    loading.value = false;
  }
}

onMounted(fetchLatest);
</script>

<template>
  <div class="latest-photos">
    <!-- Loading -->
    <div v-if="loading" class="state-container">
      <Loader2 class="w-6 h-6 animate-spin text-muted-foreground" />
      <p class="text-sm text-muted-foreground mt-2">Chargement des photos...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-container">
      <p class="text-sm text-destructive">{{ error }}</p>
    </div>

    <!-- Empty -->
    <div v-else-if="photos.length === 0" class="state-container">
      <ImageOff class="w-8 h-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground mt-2">Aucune photo pour le moment</p>
    </div>

    <!-- Photo grid -->
    <div v-else class="photo-grid">
      <div v-for="photo in photos" :key="photo.id" class="photo-card">
        <div class="photo-image" @click="lightboxPhotoId = photo.id">
          <img
            v-if="photo.thumbnail"
            :src="`data:image/jpeg;base64,${photo.thumbnail}`"
            :alt="`Photo ${photo.id}`"
          />
          <div class="photo-image-overlay">
            <ZoomIn class="w-6 h-6 text-white" />
          </div>
        </div>
        <div class="photo-info">
          <template v-if="lookupEntrance(photo.accessId)">
            <p class="station-name">{{ lookupEntrance(photo.accessId)!.stationName }}</p>
            <p class="entrance-name">{{ lookupEntrance(photo.accessId)!.entranceName }}</p>
            <div v-if="lookupEntrance(photo.accessId)!.lines.length" class="line-icons">
              <img
                v-for="line in lookupEntrance(photo.accessId)!.lines"
                :key="line.id"
                :src="line.icon_url ?? ''"
                :alt="line.name"
                class="line-icon"
              />
            </div>
          </template>
          <p v-else class="entrance-name">Entrée inconnue</p>
          <p class="photo-date">{{ formatDate(photo.createdAt) }}</p>
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
.latest-photos {
  height: 100%;
  overflow-y: auto;
  background: hsl(var(--card));
}

.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  padding: 1.5rem;
}

.photo-card {
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  transition: box-shadow 0.2s;
}

.photo-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.photo-image {
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: hsl(var(--muted));
  position: relative;
  cursor: pointer;
}

.photo-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-image-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.photo-image:hover .photo-image-overlay {
  opacity: 1;
}

.photo-info {
  padding: 0.75rem;
}

.station-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: hsl(var(--foreground));
}

.entrance-name {
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
}

.line-icons {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.375rem;
}

.line-icon {
  height: 1.125rem;
}

.photo-date {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.375rem;
}
</style>
