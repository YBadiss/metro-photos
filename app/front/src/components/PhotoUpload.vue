<script setup lang="ts">
import { ref, computed } from 'vue'
import { Progress } from '@/components/ui/progress'
import { Upload, XCircle, Image, X } from 'lucide-vue-next'

const API_URL = import.meta.env.VITE_API_URL || ''

interface ProcessingResult {
  blurredUrl: string
  blurredKey: string
  facesCount: number
}

interface FileUpload {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'processing' | 'processed' | 'error'
  progress: number
  error?: string
  key?: string
  result?: ProcessingResult
}

const uploads = ref<FileUpload[]>([])
const isDragOver = ref(false)

const pendingCount = computed(() => uploads.value.filter((u) => u.status === 'pending').length)
const uploadingCount = computed(
  () => uploads.value.filter((u) => u.status === 'uploading').length,
)
const processingCount = computed(
  () => uploads.value.filter((u) => u.status === 'processing').length,
)
const processedCount = computed(
  () => uploads.value.filter((u) => u.status === 'processed').length,
)
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
  uploads.value = uploads.value.filter((u) => u.status !== 'processed' && u.status !== 'error')
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
    pending.progress = 100

    // Step 3: Fire off face processing in parallel (don't await)
    pending.status = 'processing'
    processPhoto(pending).catch((err) => {
      pending.status = 'error'
      pending.error = err instanceof Error ? err.message : 'Processing failed'
    })
  } catch (err) {
    pending.status = 'error'
    pending.error = err instanceof Error ? err.message : 'Upload failed'
  }

  // Immediately process next upload
  processQueue()
}

async function processPhoto(upload: FileUpload) {
  const response = await fetch(`${API_URL}/process-photo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ imageKey: upload.key }),
  })

  if (!response.ok) {
    throw new Error('Face processing failed')
  }

  const data = await response.json()
  upload.result = {
    blurredUrl: data.blurredUrl,
    blurredKey: data.blurredKey,
    facesCount: data.facesCount,
  }
  upload.status = 'processed'
}

function uploadWithProgress(upload: FileUpload, url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
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

</script>

<template>
  <div class="flex flex-col gap-6 h-full">
    <!-- Dropzone: only shown when no uploads -->
    <div
      v-if="uploads.length === 0"
      class="border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer flex-1 flex items-center justify-center"
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

    <!-- Upload Summary + Grid -->
    <template v-if="uploads.length > 0">
      <!-- Summary bar -->
      <div class="flex items-center justify-between flex-shrink-0">
        <div class="flex gap-4 text-sm">
          <span v-if="pendingCount" class="text-muted-foreground">{{ pendingCount }} pending</span>
          <span v-if="uploadingCount" class="text-primary font-medium"
            >{{ uploadingCount }} uploading</span
          >
          <span v-if="processingCount" class="text-amber-600 font-medium"
            >{{ processingCount }} processing</span
          >
          <span v-if="processedCount" class="text-green-600">{{ processedCount }} completed</span>
          <span v-if="errorCount" class="text-destructive">{{ errorCount }} failed</span>
        </div>
        <button
          v-if="processedCount > 0 || errorCount > 0"
          class="text-sm text-muted-foreground hover:text-foreground transition-colors"
          @click="clearCompleted"
        >
          Clear completed
        </button>
      </div>

      <!-- Unified grid for all uploads -->
      <div
        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 flex-1 overflow-y-auto content-start"
      >
        <div
          v-for="upload in uploads"
          :key="upload.id"
          class="relative rounded-lg overflow-hidden border shadow-sm bg-card aspect-square"
        >
          <!-- Processed: show blurred image -->
          <template v-if="upload.status === 'processed'">
            <img
              :src="upload.result!.blurredUrl"
              :alt="upload.file.name"
              class="w-full h-full object-cover"
            />
            <div
              class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs px-2 py-1"
            >
              {{ upload.result!.facesCount }} face{{
                upload.result!.facesCount !== 1 ? 's' : ''
              }}
              blurred
            </div>
          </template>

          <!-- Pending / Uploading / Processing / Error: show placeholder -->
          <template v-else>
            <div class="w-full h-full flex flex-col items-center justify-center gap-3 p-4">
              <!-- Status icon -->
              <div
                v-if="upload.status === 'pending'"
                class="w-12 h-12 rounded-full bg-muted flex items-center justify-center"
              >
                <Image class="w-6 h-6 text-muted-foreground" />
              </div>
              <div
                v-else-if="upload.status === 'uploading'"
                class="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center"
              >
                <div
                  class="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"
                />
              </div>
              <div
                v-else-if="upload.status === 'processing'"
                class="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center"
              >
                <div
                  class="w-6 h-6 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"
                />
              </div>
              <div
                v-else-if="upload.status === 'error'"
                class="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center"
              >
                <XCircle class="w-6 h-6 text-destructive" />
              </div>

              <!-- Filename -->
              <p class="text-xs text-muted-foreground truncate w-full text-center">
                {{ upload.file.name }}
              </p>

              <!-- Progress bar for uploading -->
              <div v-if="upload.status === 'uploading'" class="w-full px-2">
                <Progress :model-value="upload.progress" class="h-1.5" />
              </div>

              <!-- Status label -->
              <p v-if="upload.status === 'pending'" class="text-xs text-muted-foreground">
                Pending
              </p>
              <p v-else-if="upload.status === 'uploading'" class="text-xs text-primary">
                Uploading {{ upload.progress }}%
              </p>
              <p v-else-if="upload.status === 'processing'" class="text-xs text-amber-600">
                Blurring faces...
              </p>
              <p v-else-if="upload.status === 'error'" class="text-xs text-destructive truncate w-full text-center">
                {{ upload.error }}
              </p>
            </div>

            <!-- Remove button -->
            <button
              class="absolute top-1 right-1 p-1 rounded-full bg-black/40 hover:bg-black/60 transition-colors opacity-0 group-hover:opacity-100"
              @click="removeUpload(upload.id)"
            >
              <X class="w-3.5 h-3.5 text-white" />
            </button>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>
