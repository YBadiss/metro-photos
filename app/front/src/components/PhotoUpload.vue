<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { Progress } from "@/components/ui/progress";
import { XCircle, Image, X, MapPin, Clock, Camera, Train, ChevronLeft } from "lucide-vue-next";

const API_URL = import.meta.env.VITE_API_URL || "";

interface ExifData {
  latitude?: number;
  longitude?: number;
  dateTime?: string;
  camera?: string;
}

interface MatchedEntrance {
  entrance: { id: string; name: string; short_name: number | null };
  station: { id: string; name: string; town: string };
  lines: Array<{ id: string; name: string; icon_url: string | null; color?: string }>;
  distanceMeters: number;
}

interface ProcessingResult {
  blurredUrl: string;
  blurredKey: string;
  facesCount: number;
  exif?: ExifData;
  matchedEntrance?: MatchedEntrance | null;
}

interface FileUpload {
  id: string;
  file: File;
  status: "pending" | "uploading" | "processing" | "processed" | "error";
  progress: number;
  error?: string;
  key?: string;
  result?: ProcessingResult;
}

const props = defineProps<{
  files: File[];
}>();

const emit = defineEmits<{
  flyTo: [accessId: string];
  close: [];
}>();

const uploads = ref<FileUpload[]>([]);
const selectedUploadId = ref<string | null>(null);

const pendingCount = computed(() => uploads.value.filter((u) => u.status === "pending").length);
const uploadingCount = computed(() => uploads.value.filter((u) => u.status === "uploading").length);
const processingCount = computed(
  () => uploads.value.filter((u) => u.status === "processing").length,
);
const processedCount = computed(() => uploads.value.filter((u) => u.status === "processed").length);
const errorCount = computed(() => uploads.value.filter((u) => u.status === "error").length);

const selectedUpload = computed(
  () => uploads.value.find((u) => u.id === selectedUploadId.value) ?? null,
);

function goBack() {
  selectedUploadId.value = null;
}

// Watch for new files from parent (immediate to handle initial mount)
watch(
  () => props.files,
  (newFiles) => {
    if (newFiles.length > 0) {
      addFiles(newFiles);
    }
  },
  { immediate: true },
);

function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

function addFiles(files: File[]) {
  const imageFiles = files.filter((f) => f.type.startsWith("image/"));

  for (const file of imageFiles) {
    uploads.value.push({
      id: generateId(),
      file,
      status: "pending",
      progress: 0,
    });
  }

  for (let i = 0; i < 3; i++) {
    processQueue();
  }
}

function removeUpload(id: string) {
  if (selectedUploadId.value === id) {
    selectedUploadId.value = null;
  }
  uploads.value = uploads.value.filter((u) => u.id !== id);
}

function clearCompleted() {
  if (selectedUploadId.value) {
    const selected = uploads.value.find((u) => u.id === selectedUploadId.value);
    if (selected && (selected.status === "processed" || selected.status === "error")) {
      selectedUploadId.value = null;
    }
  }
  uploads.value = uploads.value.filter((u) => u.status !== "processed" && u.status !== "error");
}

function selectUpload(upload: FileUpload) {
  if (upload.status !== "processed") return;

  selectedUploadId.value = upload.id;

  if (upload.result?.matchedEntrance) {
    emit("flyTo", upload.result.matchedEntrance.entrance.id);
  }
}

function formatCoord(lat: number, lon: number): string {
  const latDir = lat >= 0 ? "N" : "S";
  const lonDir = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(5)}° ${latDir}, ${Math.abs(lon).toFixed(5)}° ${lonDir}`;
}

function formatDateTime(date: string): string {
  return new Date(date).toLocaleString();
}

async function processQueue() {
  const pending = uploads.value.find((u) => u.status === "pending");
  if (!pending || uploadingCount.value >= 3) return;

  pending.status = "uploading";

  try {
    const urlResponse = await fetch(`${API_URL}/upload-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: pending.file.name,
        contentType: pending.file.type,
      }),
    });

    if (!urlResponse.ok) {
      throw new Error("Failed to get upload URL");
    }

    const { uploadUrl, key } = await urlResponse.json();
    pending.key = key;
    pending.progress = 10;

    await uploadWithProgress(pending, uploadUrl);
    pending.progress = 100;

    pending.status = "processing";
    processPhoto(pending)
      .catch((err) => {
        pending.status = "error";
        pending.error = err instanceof Error ? err.message : "Processing failed";
      })
      .finally(() => {
        processQueue();
      });
  } catch (err) {
    pending.status = "error";
    pending.error = err instanceof Error ? err.message : "Upload failed";
  }

  processQueue();
}

async function processPhoto(upload: FileUpload) {
  const response = await fetch(`${API_URL}/process-photo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ imageKey: upload.key }),
  });

  if (!response.ok) {
    throw new Error("Face processing failed");
  }

  const data = await response.json();
  upload.result = {
    blurredUrl: data.blurredUrl,
    blurredKey: data.blurredKey,
    facesCount: data.facesCount,
    exif: data.exif,
    matchedEntrance: data.matchedEntrance,
  };
  upload.status = "processed";
}

function uploadWithProgress(upload: FileUpload, url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        upload.progress = 10 + Math.round((e.loaded / e.total) * 85);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));
    xhr.addEventListener("abort", () => reject(new Error("Upload cancelled")));

    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", upload.file.type);
    xhr.send(upload.file);
  });
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- ==================== DETAIL VIEW ==================== -->
    <template v-if="selectedUpload">
      <!-- Detail header with back button -->
      <div class="flex items-center gap-2 px-3 py-3 border-b flex-shrink-0">
        <button class="p-1 hover:bg-muted rounded transition-colors" @click="goBack">
          <ChevronLeft class="w-4 h-4 text-muted-foreground" />
        </button>
        <h3 class="font-semibold text-sm truncate">{{ selectedUpload.file.name }}</h3>
      </div>

      <!-- Detail content -->
      <div class="flex-1 overflow-y-auto">
        <!-- Large preview image -->
        <div class="border-b">
          <img
            :src="selectedUpload.result!.blurredUrl"
            :alt="selectedUpload.file.name"
            class="w-full object-contain max-h-64 bg-black/5"
          />
        </div>

        <div class="p-4 flex flex-col gap-4">
          <!-- Matched Metro Entrance -->
          <div v-if="selectedUpload.result?.matchedEntrance" class="flex items-start gap-3">
            <Train class="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
            <div class="min-w-0">
              <p class="text-xs text-muted-foreground">Nearest Metro Entrance</p>
              <p class="font-medium">
                {{ selectedUpload.result.matchedEntrance.station.name }}
              </p>
              <p class="text-sm">{{ selectedUpload.result.matchedEntrance.entrance.name }}</p>
              <p class="text-xs text-muted-foreground mt-0.5">
                {{ selectedUpload.result.matchedEntrance.distanceMeters }}m away &middot;
                {{ selectedUpload.result.matchedEntrance.station.town }}
              </p>
              <div
                v-if="selectedUpload.result.matchedEntrance.lines.length"
                class="flex gap-1 mt-1.5"
              >
                <img
                  v-for="line in selectedUpload.result.matchedEntrance.lines"
                  :key="line.id"
                  :src="line.icon_url ?? ''"
                  :alt="line.name"
                  class="h-5"
                />
              </div>
            </div>
          </div>
          <div v-else class="flex items-center gap-3">
            <Train class="w-5 h-5 text-muted-foreground flex-shrink-0" />
            <p class="text-sm text-muted-foreground italic">No metro entrance nearby</p>
          </div>

          <!-- GPS Location -->
          <div
            v-if="
              selectedUpload.result?.exif?.latitude != null &&
              selectedUpload.result?.exif?.longitude != null
            "
            class="flex items-start gap-3"
          >
            <MapPin class="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Location</p>
              <p class="text-sm">
                {{
                  formatCoord(
                    selectedUpload.result.exif.latitude,
                    selectedUpload.result.exif.longitude,
                  )
                }}
              </p>
              <a
                :href="`https://www.google.com/maps?q=${selectedUpload.result.exif.latitude},${selectedUpload.result.exif.longitude}`"
                target="_blank"
                rel="noopener"
                class="text-xs text-primary hover:underline"
              >
                View on Google Maps
              </a>
            </div>
          </div>
          <div v-else class="flex items-center gap-3">
            <MapPin class="w-5 h-5 text-muted-foreground flex-shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Location</p>
              <p class="text-sm text-muted-foreground italic">No GPS data</p>
            </div>
          </div>

          <!-- Date/Time -->
          <div v-if="selectedUpload.result?.exif?.dateTime" class="flex items-start gap-3">
            <Clock class="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Taken</p>
              <p class="text-sm">{{ formatDateTime(selectedUpload.result.exif.dateTime) }}</p>
            </div>
          </div>
          <div v-else class="flex items-center gap-3">
            <Clock class="w-5 h-5 text-muted-foreground flex-shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Taken</p>
              <p class="text-sm text-muted-foreground italic">No date data</p>
            </div>
          </div>

          <!-- Camera -->
          <div v-if="selectedUpload.result?.exif?.camera" class="flex items-start gap-3">
            <Camera class="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Camera</p>
              <p class="text-sm">{{ selectedUpload.result.exif.camera }}</p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ==================== LIST VIEW ==================== -->
    <template v-else>
      <!-- List header -->
      <div class="flex items-center justify-between px-4 py-3 border-b flex-shrink-0">
        <h3 class="font-semibold text-sm">Uploads</h3>
        <button class="p-1 hover:bg-muted rounded transition-colors" @click="emit('close')">
          <X class="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      <!-- Summary bar -->
      <div
        v-if="uploads.length > 0"
        class="flex items-center justify-between px-4 py-2 border-b flex-shrink-0"
      >
        <div class="flex gap-3 text-xs flex-wrap">
          <span v-if="pendingCount" class="text-muted-foreground">{{ pendingCount }} pending</span>
          <span v-if="uploadingCount" class="text-primary font-medium"
            >{{ uploadingCount }} uploading</span
          >
          <span v-if="processingCount" class="text-amber-600 font-medium"
            >{{ processingCount }} processing</span
          >
          <span v-if="processedCount" class="text-green-600">{{ processedCount }} done</span>
          <span v-if="errorCount" class="text-destructive">{{ errorCount }} failed</span>
        </div>
        <button
          v-if="processedCount > 0 || errorCount > 0"
          class="text-xs text-muted-foreground hover:text-foreground transition-colors"
          @click="clearCompleted"
        >
          Clear
        </button>
      </div>

      <!-- Upload grid -->
      <div class="flex-1 overflow-y-auto">
        <div class="grid grid-cols-2 gap-2 p-4 content-start">
          <div
            v-for="upload in uploads"
            :key="upload.id"
            class="relative rounded-lg overflow-hidden border shadow-sm bg-card aspect-square"
            :class="{
              'cursor-pointer hover:ring-2 hover:ring-primary/50': upload.status === 'processed',
            }"
            @click="selectUpload(upload)"
          >
            <!-- Processed: show blurred image -->
            <template v-if="upload.status === 'processed'">
              <img
                :src="upload.result!.blurredUrl"
                :alt="upload.file.name"
                class="w-full h-full object-cover"
              />
            </template>

            <!-- Pending / Uploading / Processing / Error -->
            <template v-else>
              <div class="w-full h-full flex flex-col items-center justify-center gap-2 p-3">
                <div
                  v-if="upload.status === 'pending'"
                  class="w-10 h-10 rounded-full bg-muted flex items-center justify-center"
                >
                  <Image class="w-5 h-5 text-muted-foreground" />
                </div>
                <div
                  v-else-if="upload.status === 'uploading'"
                  class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center"
                >
                  <div
                    class="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"
                  />
                </div>
                <div
                  v-else-if="upload.status === 'processing'"
                  class="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center"
                >
                  <div
                    class="w-5 h-5 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"
                  />
                </div>
                <div
                  v-else-if="upload.status === 'error'"
                  class="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center"
                >
                  <XCircle class="w-5 h-5 text-destructive" />
                </div>

                <p class="text-xs text-muted-foreground truncate w-full text-center">
                  {{ upload.file.name }}
                </p>

                <div v-if="upload.status === 'uploading'" class="w-full">
                  <Progress :model-value="upload.progress" class="h-1" />
                </div>

                <p v-if="upload.status === 'pending'" class="text-xs text-muted-foreground">
                  Pending
                </p>
                <p v-else-if="upload.status === 'uploading'" class="text-xs text-primary">
                  {{ upload.progress }}%
                </p>
                <p v-else-if="upload.status === 'processing'" class="text-xs text-amber-600">
                  Processing...
                </p>
                <p
                  v-else-if="upload.status === 'error'"
                  class="text-xs text-destructive truncate w-full text-center"
                >
                  {{ upload.error }}
                </p>
              </div>

              <button
                class="absolute top-1 right-1 p-1 rounded-full bg-black/40 hover:bg-black/60 transition-colors"
                @click.stop="removeUpload(upload.id)"
              >
                <X class="w-3 h-3 text-white" />
              </button>
            </template>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
