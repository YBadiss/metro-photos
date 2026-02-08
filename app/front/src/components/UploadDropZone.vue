<script setup lang="ts">
import { ref } from "vue";
import { Upload } from "lucide-vue-next";

withDefaults(
  defineProps<{
    compact?: boolean;
  }>(),
  { compact: false },
);

const emit = defineEmits<{
  "files-selected": [files: File[]];
}>();

const isDragging = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);

function onDrop(e: DragEvent) {
  isDragging.value = false;
  const files = e.dataTransfer?.files;
  if (files && files.length > 0) {
    emit("files-selected", Array.from(files));
  }
}

function onDragOver(e: DragEvent) {
  e.preventDefault();
  isDragging.value = true;
}

function onDragLeave() {
  isDragging.value = false;
}

function onFileInput(e: Event) {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    emit("files-selected", Array.from(target.files));
  }
  target.value = "";
}
</script>

<template>
  <!-- Full-area drop zone -->
  <div
    v-if="!compact"
    class="flex flex-col items-center justify-center gap-4 border-2 border-dashed rounded-lg p-12 transition-colors cursor-pointer"
    :class="
      isDragging
        ? 'border-primary bg-primary/5'
        : 'border-muted-foreground/25 hover:border-primary/50'
    "
    @drop.prevent="onDrop"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @click="fileInputRef?.click()"
  >
    <Upload class="w-10 h-10 text-muted-foreground" />
    <div class="text-center">
      <p class="text-sm font-medium">Drop photos here or click to browse</p>
      <p class="text-xs text-muted-foreground mt-1">Supports JPEG, PNG, and other image formats</p>
    </div>
    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      multiple
      class="hidden"
      @change="onFileInput"
    />
  </div>

  <!-- Compact bar -->
  <div
    v-else
    class="flex items-center gap-3 px-4 py-2 border-b border-dashed transition-colors cursor-pointer"
    :class="isDragging ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'"
    @drop.prevent="onDrop"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @click="fileInputRef?.click()"
  >
    <Upload class="w-4 h-4 text-muted-foreground flex-shrink-0" />
    <p class="text-xs text-muted-foreground">Drop more photos or click to browse</p>
    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      multiple
      class="hidden"
      @change="onFileInput"
    />
  </div>
</template>
