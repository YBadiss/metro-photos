<script setup lang="ts">
import { ref, onMounted, watch, type Ref } from "vue";
import MetroMap from "./components/MetroMap.vue";
import PhotoUpload from "./components/PhotoUpload.vue";
import InfoModal from "./components/InfoModal.vue";
import { Upload } from "lucide-vue-next";
import type { Zone } from "./types/metro";

const zones: Ref<Zone[]> = ref([]);
const loading = ref(true);
const error: Ref<string | null> = ref(null);
const isInfoModalOpen = ref(false);
const metroMapRef = ref<InstanceType<typeof MetroMap> | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

const showSidebar = ref(false);
const pendingFiles = ref<File[]>([]);

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

function handleFileInput(e: Event) {
  const target = e.target as HTMLInputElement;
  const files = target.files;
  if (files && files.length > 0) {
    pendingFiles.value = Array.from(files);
    showSidebar.value = true;
  }
  target.value = "";
}

function handleFlyTo(accessId: string) {
  metroMapRef.value?.flyToEntrance(accessId);
}

function closeSidebar() {
  showSidebar.value = false;
}

watch(showSidebar, () => {
  metroMapRef.value?.invalidateSize();
});
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Metro, Boulot, Photos!</h1>
      <div class="header-buttons">
        <button class="header-button" aria-label="Upload photos" @click="fileInputRef?.click()">
          <Upload class="w-5 h-5" />
        </button>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          multiple
          style="display: none"
          @change="handleFileInput"
        />
        <button class="header-button" aria-label="About this site" @click="isInfoModalOpen = true">
          ?
        </button>
      </div>
    </header>

    <div class="content">
      <div v-if="loading" class="loading">Loading metro data...</div>
      <div v-else-if="error" class="error">Error: {{ error }}</div>
      <template v-else>
        <div class="map-wrapper">
          <MetroMap ref="metroMapRef" :zones="zones" />
        </div>
        <div v-if="showSidebar" class="sidebar">
          <PhotoUpload :files="pendingFiles" @fly-to="handleFlyTo" @close="closeSidebar" />
        </div>
      </template>
    </div>

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

.content {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.map-wrapper {
  flex: 1;
  min-width: 0;
  background: hsl(var(--card));
}

.sidebar {
  width: 22rem;
  flex-shrink: 0;
  background: hsl(var(--card));
  border-left: 1px solid hsl(var(--border));
}

.loading,
.error {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  font-size: 1.125rem;
}

.error {
  color: hsl(var(--destructive));
}
</style>
