<script setup lang="ts">
import { ref, onMounted, type Ref } from 'vue'
import MetroMap from './components/MetroMap.vue'
import InfoModal from './components/InfoModal.vue'
import type { Zone } from './types/metro'

const zones: Ref<Zone[]> = ref([])
const loading = ref(true)
const error: Ref<string | null> = ref(null)
const isInfoModalOpen = ref(false)

onMounted(async () => {
  try {
    // Load the zones_metro.json file
    // In development, this will be served from the public folder
    // For production, you can adjust the path as needed
    const response = await fetch('/data/zones_metro.json')
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
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Metro, Boulot, Photos!</h1>
      <button class="info-button" aria-label="About this site" @click="isInfoModalOpen = true">
        ?
      </button>
    </header>
    <div v-if="loading" class="loading">Loading metro data...</div>
    <div v-else-if="error" class="error">Error: {{ error }}</div>
    <div v-else class="map-wrapper">
      <MetroMap :zones="zones" />
    </div>

    <InfoModal :is-open="isInfoModalOpen" @close="isInfoModalOpen = false" />
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f5f5;
}

.app {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 20px;
  gap: 20px;
}

.header {
  text-align: center;
  flex-shrink: 0;
  position: relative;
}

.header h1 {
  font-size: 48px;
  font-weight: 700;
  color: #333;
  margin: 0;
  letter-spacing: -0.5px;
}

.info-button {
  position: absolute;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: white;
  border: 2px solid #ddd;
  color: #666;
  font-size: 24px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.info-button:hover {
  background: #333;
  color: white;
  border-color: #333;
  transform: translateY(-50%) scale(1.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.map-wrapper {
  flex: 1;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.loading,
.error {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  font-size: 18px;
}

.error {
  color: #d32f2f;
}
</style>
