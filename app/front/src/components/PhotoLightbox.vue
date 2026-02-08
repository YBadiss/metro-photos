<script setup lang="ts">
import { ref, watch } from "vue";
import { X, Loader2 } from "lucide-vue-next";

const API_URL = import.meta.env.VITE_API_URL || "";

const props = defineProps<{
  photoId: number;
}>();

const emit = defineEmits<{
  close: [];
}>();

const fullUrl = ref<string | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

async function fetchUrl(id: number) {
  loading.value = true;
  error.value = null;
  fullUrl.value = null;

  try {
    const response = await fetch(`${API_URL}/photos/${id}/url`);
    if (!response.ok) throw new Error("Impossible de charger l'image");
    const data = await response.json();
    fullUrl.value = data.url;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Erreur inconnue";
  } finally {
    loading.value = false;
  }
}

watch(() => props.photoId, (id) => fetchUrl(id), { immediate: true });
</script>

<template>
  <Teleport to="body">
    <Transition name="lightbox">
      <div class="lightbox-overlay" @click="emit('close')">
        <button class="close-button" aria-label="Fermer" @click.stop="emit('close')">
          <X class="w-6 h-6" />
        </button>

        <div class="lightbox-content" @click.stop>
          <!-- Loading -->
          <div v-if="loading" class="lightbox-state">
            <Loader2 class="w-8 h-8 animate-spin text-white/70" />
          </div>

          <!-- Error -->
          <div v-else-if="error" class="lightbox-state">
            <p class="text-white/70 text-sm">{{ error }}</p>
          </div>

          <!-- Image -->
          <img
            v-else-if="fullUrl"
            :src="fullUrl"
            alt="Photo pleine résolution"
            class="lightbox-image"
          />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.lightbox-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 20px;
}

.close-button {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  cursor: pointer;
  transition: background-color 0.2s;
  z-index: 1;
}

.close-button:hover {
  background: rgba(255, 255, 255, 0.25);
}

.lightbox-content {
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 90vw;
  max-height: 90vh;
}

.lightbox-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  min-width: 200px;
}

.lightbox-image {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 4px;
}

/* Transitions */
.lightbox-enter-active,
.lightbox-leave-active {
  transition: opacity 0.3s ease;
}

.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}
</style>
