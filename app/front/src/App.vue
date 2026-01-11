<script setup lang="ts">
import { ref, onMounted, type Ref } from 'vue'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import MetroMap from './components/MetroMap.vue'
import PhotoUpload from './components/PhotoUpload.vue'
import InfoModal from './components/InfoModal.vue'
import { Map, Upload } from 'lucide-vue-next'
import type { Zone } from './types/metro'

const zones: Ref<Zone[]> = ref([])
const loading = ref(true)
const error: Ref<string | null> = ref(null)
const isInfoModalOpen = ref(false)
const metroMapRef = ref<InstanceType<typeof MetroMap> | null>(null)

// API base URL from environment
const API_URL = import.meta.env.VITE_API_URL || ''

onMounted(async () => {
  try {
    const response = await fetch(`${API_URL}/zones_metro`)
    if (!response.ok) {
      throw new Error(`Failed to load data: ${response.statusText}`)
    }
    zones.value = await response.json()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error occurred'
    console.error('Error loading metro data:', e)
  } finally {
    loading.value = false
  }
})

function onTabChange(value: string | number) {
  if (value === 'map') {
    metroMapRef.value?.invalidateSize()
  }
}
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Metro, Boulot, Photos!</h1>
      <button class="info-button" aria-label="About this site" @click="isInfoModalOpen = true">
        ?
      </button>
    </header>

    <Tabs default-value="map" class="flex-1 flex flex-col min-h-0" @update:model-value="onTabChange">
      <TabsList class="self-center">
        <TabsTrigger value="map" class="gap-2">
          <Map class="w-4 h-4" />
          Map
        </TabsTrigger>
        <TabsTrigger value="upload" class="gap-2">
          <Upload class="w-4 h-4" />
          Upload
        </TabsTrigger>
      </TabsList>

      <TabsContent value="map" class="flex-1 min-h-0 h-full data-[state=active]:flex data-[state=active]:flex-col">
        <div v-if="loading" class="loading">Loading metro data...</div>
        <div v-else-if="error" class="error">Error: {{ error }}</div>
        <div v-else class="map-wrapper flex-1">
          <MetroMap ref="metroMapRef" :zones="zones" />
        </div>
      </TabsContent>

      <TabsContent value="upload" class="flex-1 min-h-0 h-full data-[state=active]:flex data-[state=active]:flex-col">
        <div class="upload-wrapper flex-1">
          <PhotoUpload />
        </div>
      </TabsContent>
    </Tabs>

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

.info-button {
  position: absolute;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
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

.info-button:hover {
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  border-color: hsl(var(--foreground));
  transform: translateY(-50%) scale(1.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.map-wrapper {
  height: 100%;
  background: hsl(var(--card));
  border-radius: 0.75rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.upload-wrapper {
  height: 100%;
  background: hsl(var(--card));
  border-radius: 0.75rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  overflow: hidden;
}

.loading,
.error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 1.125rem;
}

.error {
  color: hsl(var(--destructive));
}
</style>
