<script setup>
import { ref, onMounted } from 'vue'
import MetroMap from './components/MetroMap.vue'

const zones = ref([])
const loading = ref(true)
const error = ref(null)

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
    error.value = e.message
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
    </header>
    <div v-if="loading" class="loading">
      Loading metro data...
    </div>
    <div v-else-if="error" class="error">
      Error: {{ error }}
    </div>
    <div v-else class="map-wrapper">
      <MetroMap :zones="zones" />
    </div>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
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
}

.header h1 {
  font-size: 48px;
  font-weight: 700;
  color: #333;
  margin: 0;
  letter-spacing: -0.5px;
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
