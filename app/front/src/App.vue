<script setup lang="ts">
import { ref, onMounted, watch, nextTick, type Ref } from "vue";
import MetroMap from "./components/MetroMap.vue";
import PhotoUpload from "./components/PhotoUpload.vue";
import PhotoDetailSidebar from "./components/PhotoDetailSidebar.vue";
import InfoModal from "./components/InfoModal.vue";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Map, Upload } from "lucide-vue-next";
import type { Zone } from "./types/metro";
import type { FileUpload } from "./types/uploads";

const zones: Ref<Zone[]> = ref([]);
const loading = ref(true);
const error: Ref<string | null> = ref(null);
const isInfoModalOpen = ref(false);
const metroMapRef = ref<InstanceType<typeof MetroMap> | null>(null);

const activeTab = ref("map");
const selectedUpload = ref<FileUpload | null>(null);

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
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Metro, Boulot, Photos!</h1>
      <div class="header-buttons">
        <button class="header-button" aria-label="About this site" @click="isInfoModalOpen = true">
          ?
        </button>
      </div>
    </header>

    <div v-if="loading" class="loading">Loading metro data...</div>
    <div v-else-if="error" class="error">Error: {{ error }}</div>
    <template v-else>
      <Tabs v-model="activeTab" class="tabs-root">
        <TabsList class="tabs-list">
          <TabsTrigger value="map" class="tabs-trigger">
            <Map class="w-4 h-4" />
            Map
          </TabsTrigger>
          <TabsTrigger value="uploads" class="tabs-trigger">
            <Upload class="w-4 h-4" />
            Uploads
          </TabsTrigger>
        </TabsList>

        <!-- Map tab: forceMount keeps Leaflet alive, hidden via CSS -->
        <TabsContent
          value="map"
          force-mount
          class="tab-content"
          :class="{ hidden: activeTab !== 'map' }"
        >
          <div class="map-wrapper">
            <MetroMap ref="metroMapRef" :zones="zones" />
          </div>
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
  padding: 1.25rem;
  gap: 1.25rem;
}

.header {
  text-align: center;
  flex-shrink: 0;
  position: relative;
}

.header h1 {
  font-size: 3rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  letter-spacing: -0.025em;
}

.header-buttons {
  position: absolute;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  display: flex;
  gap: 0.5rem;
}

.header-button {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  background: hsl(var(--background));
  border: 2px solid hsl(var(--border));
  color: hsl(var(--muted-foreground));
  font-size: 1.5rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.header-button:hover {
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  border-color: hsl(var(--foreground));
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.tabs-root {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.tabs-list {
  flex-shrink: 0;
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

.tab-content.hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.map-wrapper {
  width: 100%;
  height: 100%;
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
