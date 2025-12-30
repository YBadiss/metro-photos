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
    <div v-if="loading" class="loading">
      Loading metro data...
    </div>
    <div v-else-if="error" class="error">
      Error: {{ error }}
    </div>
    <MetroMap v-else :zones="zones" />
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
}

.app {
  width: 100%;
  height: 100vh;
}

.loading,
.error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  font-size: 18px;
}

.error {
  color: #d32f2f;
}
</style>
