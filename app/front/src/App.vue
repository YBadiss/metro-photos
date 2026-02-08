<script setup lang="ts">
import { ref, onMounted, watch, nextTick, type Ref } from "vue";
import MetroMap from "./components/MetroMap.vue";
import PhotoUpload from "./components/PhotoUpload.vue";
import PhotoDetailSidebar from "./components/PhotoDetailSidebar.vue";
import EntrancePhotosSidebar from "./components/EntrancePhotosSidebar.vue";
import LatestPhotos from "./components/LatestPhotos.vue";
import InfoModal from "./components/InfoModal.vue";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Map, Upload, Images } from "lucide-vue-next";
import type { Zone } from "./types/metro";
import type { FileUpload } from "./types/uploads";

const zones: Ref<Zone[]> = ref([]);
const loading = ref(true);
const error: Ref<string | null> = ref(null);
const isInfoModalOpen = ref(false);
const metroMapRef = ref<InstanceType<typeof MetroMap> | null>(null);

const activeTab = ref("map");
const selectedUpload = ref<FileUpload | null>(null);
const selectedZoneId = ref<string | null>(null);
const selectedAccessId = ref<string | null>(null);

// API base URL from environment
const API_URL = import.meta.env.VITE_API_URL || "";

onMounted(async () => {
  try {
    const response = await fetch(`${API_URL}/zones_metro`);
    if (!response.ok) {
      throw new Error(`Failed to load data: ${response.statusText}`);
    }
    zones.value = await response.json();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Unknown error occurred";
    console.error("Error loading metro data:", e);
  } finally {
    loading.value = false;
  }
});

// When switching back to map tab, invalidate Leaflet size
watch(activeTab, (tab) => {
  if (tab === "map") {
    nextTick(() => {
      metroMapRef.value?.invalidateSize();
    });
  }
});

function handlePhotoSelected(upload: FileUpload) {
  selectedUpload.value = upload;
}

function handleValidated(_photoId: number) {
  if (selectedUpload.value) {
    selectedUpload.value.status = "validated";
  }
}

function handleCloseSidebar() {
  selectedUpload.value = null;
}

function handleStationClicked(zoneId: string | null) {
  selectedZoneId.value = zoneId;
  if (!zoneId) selectedAccessId.value = null;
}

function handleEntranceClicked(accessId: string | null) {
  selectedAccessId.value = accessId;
}

watch(selectedZoneId, () => {
  nextTick(() => {
    metroMapRef.value?.invalidateSize();
  });
});
</script>

<template>
  <div class="app">
    <div v-if="loading" class="loading">Chargement des données métro...</div>
    <div v-else-if="error" class="error">Erreur : {{ error }}</div>
    <template v-else>
      <Tabs v-model="activeTab" class="tabs-root">
        <div class="app-bar">
          <span class="app-title">Métro, Boulot, Photos&nbsp;!</span>
          <TabsList class="tabs-list">
            <TabsTrigger value="map" class="tabs-trigger">
              <Map class="w-4 h-4" />
              <span class="tab-label">Carte</span>
            </TabsTrigger>
            <TabsTrigger value="uploads" class="tabs-trigger">
              <Upload class="w-4 h-4" />
              <span class="tab-label">Ajout Photos</span>
            </TabsTrigger>
            <TabsTrigger value="gallery" class="tabs-trigger">
              <Images class="w-4 h-4" />
              <span class="tab-label">Derniers Ajouts</span>
            </TabsTrigger>
          </TabsList>
          <button class="info-button" aria-label="À propos" @click="isInfoModalOpen = true">
            ?
          </button>
        </div>

        <!-- Map tab: forceMount keeps Leaflet alive, hidden via CSS -->
        <TabsContent
          value="map"
          force-mount
          class="tab-content"
          :class="{ hidden: activeTab !== 'map' }"
        >
          <div class="map-layout">
            <div class="map-wrapper">
              <MetroMap ref="metroMapRef" :zones="zones" @station-clicked="handleStationClicked" @entrance-clicked="handleEntranceClicked" />
            </div>
            <div v-if="selectedZoneId" class="map-sidebar">
              <EntrancePhotosSidebar
                :zone-id="selectedZoneId"
                :filtered-access-id="selectedAccessId"
                :zones="zones"
                @close="selectedZoneId = null; selectedAccessId = null"
              />
            </div>
          </div>
        </TabsContent>

        <!-- Gallery tab -->
        <TabsContent value="gallery" class="tab-content">
          <LatestPhotos :zones="zones" />
        </TabsContent>

        <!-- Uploads tab -->
        <TabsContent value="uploads" class="tab-content">
          <div class="uploads-layout">
            <div class="uploads-grid">
              <PhotoUpload @photo-selected="handlePhotoSelected" />
            </div>
            <div v-if="selectedUpload" class="uploads-sidebar">
              <PhotoDetailSidebar
                :upload="selectedUpload"
                :zones="zones"
                @close="handleCloseSidebar"
                @validated="handleValidated"
              />
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </template>

    <InfoModal :is-open="isInfoModalOpen" @close="isInfoModalOpen = false" />
  </div>
</template>

<style scoped>
.app {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 0.5rem;
  gap: 0.5rem;
}

.app-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.app-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  white-space: nowrap;
  letter-spacing: -0.025em;
}

.info-button {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 9999px;
  background: hsl(var(--background));
  border: 2px solid hsl(var(--border));
  color: hsl(var(--muted-foreground));
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.info-button:hover {
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  border-color: hsl(var(--foreground));
}

.tabs-root {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.tabs-list {
  flex: 1;
  display: flex;
  justify-content: center;
}

.tabs-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.tab-content {
  flex: 1;
  min-height: 0;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

@media (max-width: 640px) {
  .app-title {
    display: none;
  }

  .tab-label {
    display: none;
  }

  .app-bar {
    gap: 0.5rem;
  }

  .map-layout,
  .uploads-layout {
    flex-direction: column;
  }

  .map-wrapper,
  .uploads-grid {
    flex: none;
    height: 50%;
  }

  .map-sidebar,
  .uploads-sidebar {
    width: auto;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
}

.tab-content.hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.map-layout {
  display: flex;
  height: 100%;
}

.map-wrapper {
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background: hsl(var(--card));
}

.map-sidebar {
  width: 24rem;
  flex-shrink: 0;
  background: hsl(var(--card));
}

.uploads-layout {
  display: flex;
  height: 100%;
  background: hsl(var(--card));
}

.uploads-grid {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.uploads-sidebar {
  width: 24rem;
  flex-shrink: 0;
}

.loading,
.error {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  flex: 1;
  font-size: 1.125rem;
}

.error {
  color: hsl(var(--destructive));
}
</style>
