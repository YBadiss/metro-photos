<script setup lang="ts">
import { ref, computed } from 'vue'
import { Progress } from '@/components/ui/progress'
import { Upload, CheckCircle, XCircle, Image, X } from 'lucide-vue-next'

const API_URL = import.meta.env.VITE_API_URL || ''

interface FileUpload {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  error?: string
  key?: string
}

const uploads = ref<FileUpload[]>([])
const isDragOver = ref(false)

const pendingCount = computed(() => uploads.value.filter((u) => u.status === 'pending').length)
const uploadingCount = computed(() => uploads.value.filter((u) => u.status === 'uploading').length)
const successCount = computed(() => uploads.value.filter((u) => u.status === 'success').length)
const errorCount = computed(() => uploads.value.filter((u) => u.status === 'error').length)

function generateId(): string {
  return Math.random().toString(36).substring(2, 9)
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = true
}

function handleDragLeave() {
  isDragOver.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false

  const files = e.dataTransfer?.files
  if (files) {
    addFiles(Array.from(files))
  }
}

function handleFileInput(e: Event) {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (files) {
    addFiles(Array.from(files))
  }
  target.value = '' // Reset input
}

function addFiles(files: File[]) {
  const imageFiles = files.filter((f) => f.type.startsWith('image/'))

  for (const file of imageFiles) {
    uploads.value.push({
      id: generateId(),
      file,
      status: 'pending',
      progress: 0,
    })
  }

  processQueue()
}

function removeUpload(id: string) {
  uploads.value = uploads.value.filter((u) => u.id !== id)
}

function clearCompleted() {
  uploads.value = uploads.value.filter((u) => u.status !== 'success' && u.status !== 'error')
}

async function processQueue() {
  const pending = uploads.value.find((u) => u.status === 'pending')
  if (!pending || uploadingCount.value >= 3) return // Max 3 concurrent uploads

  pending.status = 'uploading'

  try {
    // Step 1: Get presigned URL
    const urlResponse = await fetch(`${API_URL}/upload-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: pending.file.name,
        contentType: pending.file.type,
      }),
    })

    if (!urlResponse.ok) {
      throw new Error('Failed to get upload URL')
    }

    const { uploadUrl, key } = await urlResponse.json()
    pending.key = key
    pending.progress = 10

    // Step 2: Upload to S3 with progress tracking
    await uploadWithProgress(pending, uploadUrl)

    pending.status = 'success'
    pending.progress = 100
  } catch (err) {
    pending.status = 'error'
    pending.error = err instanceof Error ? err.message : 'Upload failed'
  }

  // Process next in queue
  processQueue()
}

function uploadWithProgress(upload: FileUpload, url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        // Map 10-95% to upload progress (0% reserved for getting URL, 100% for completion)
        upload.progress = 10 + Math.round((e.loaded / e.total) * 85)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve()
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`))
      }
    })

    xhr.addEventListener('error', () => reject(new Error('Network error')))
    xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')))

    xhr.open('PUT', url)
    xhr.setRequestHeader('Content-Type', upload.file.type)
    xhr.send(upload.file)
  })
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<template>
  <div class="flex flex-col gap-6 h-full">
    <!-- Dropzone -->
    <div
      class="border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer"
      :class="
        isDragOver
          ? 'border-primary bg-primary/5 scale-[1.01]'
          : 'border-border hover:border-primary/50 hover:bg-muted/50'
      "
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      @click="($refs.fileInput as HTMLInputElement).click()"
    >
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        multiple
        style="display: none"
        @change="handleFileInput"
      />
      <div class="flex flex-col items-center gap-4">
        <div class="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
          <Upload class="w-8 h-8 text-primary" />
        </div>
        <div>
          <p class="text-lg font-medium">Drop photos here or click to browse</p>
          <p class="text-sm text-muted-foreground mt-1">Supports JPG, PNG, WebP</p>
        </div>
      </div>
    </div>

    <!-- Upload Summary -->
    <div v-if="uploads.length > 0" class="flex items-center justify-between">
      <div class="flex gap-4 text-sm">
        <span v-if="pendingCount" class="text-muted-foreground">{{ pendingCount }} pending</span>
        <span v-if="uploadingCount" class="text-primary font-medium"
          >{{ uploadingCount }} uploading</span
        >
        <span v-if="successCount" class="text-green-600">{{ successCount }} completed</span>
        <span v-if="errorCount" class="text-destructive">{{ errorCount }} failed</span>
      </div>
      <button
        v-if="successCount > 0 || errorCount > 0"
        class="text-sm text-muted-foreground hover:text-foreground transition-colors"
        @click="clearCompleted"
      >
        Clear completed
      </button>
    </div>

    <!-- Upload List -->
    <div v-if="uploads.length > 0" class="flex-1 overflow-auto space-y-3">
      <div
        v-for="upload in uploads"
        :key="upload.id"
        class="flex items-center gap-4 p-4 bg-card rounded-lg border shadow-sm"
      >
        <!-- Thumbnail / Icon -->
        <div
          class="w-12 h-12 rounded-lg bg-muted flex items-center justify-center overflow-hidden flex-shrink-0"
        >
          <Image class="w-6 h-6 text-muted-foreground" />
        </div>

        <!-- File Info -->
        <div class="flex-1 min-w-0">
          <p class="font-medium truncate">{{ upload.file.name }}</p>
          <p class="text-sm text-muted-foreground">{{ formatSize(upload.file.size) }}</p>

          <!-- Progress Bar -->
          <div v-if="upload.status === 'uploading'" class="mt-2">
            <Progress :model-value="upload.progress" class="h-2" />
          </div>

          <!-- Error Message -->
          <p v-if="upload.status === 'error'" class="text-sm text-destructive mt-1">
            {{ upload.error }}
          </p>
        </div>

        <!-- Status Icon -->
        <div class="flex-shrink-0">
          <div
            v-if="upload.status === 'pending'"
            class="w-8 h-8 rounded-full bg-muted flex items-center justify-center"
          >
            <div class="w-2 h-2 rounded-full bg-muted-foreground" />
          </div>
          <div
            v-else-if="upload.status === 'uploading'"
            class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center"
          >
            <div
              class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"
            />
          </div>
          <CheckCircle v-else-if="upload.status === 'success'" class="w-8 h-8 text-green-600" />
          <XCircle v-else-if="upload.status === 'error'" class="w-8 h-8 text-destructive" />
        </div>

        <!-- Remove Button -->
        <button
          class="p-1 hover:bg-muted rounded transition-colors flex-shrink-0"
          @click="removeUpload(upload.id)"
        >
          <X class="w-5 h-5 text-muted-foreground" />
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="flex-1 flex items-center justify-center text-muted-foreground">
      <p>No photos uploaded yet</p>
    </div>
  </div>
</template>
