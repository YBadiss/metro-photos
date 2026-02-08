<script setup lang="ts">
import { ref, computed } from "vue";
import { Progress } from "@/components/ui/progress";
import { XCircle, Image, X, Check, MapPin, ShieldCheck, CheckCircle2, ScanEye } from "lucide-vue-next";
import type { FileUpload } from "@/types/uploads";
import UploadDropZone from "./UploadDropZone.vue";

const API_URL = import.meta.env.VITE_API_URL || "";

const emit = defineEmits<{
  "photo-selected": [upload: FileUpload];
}>();

const uploads = ref<FileUpload[]>([]);

const pendingCount = computed(() => uploads.value.filter((u) => u.status === "pending").length);
const uploadingCount = computed(() => uploads.value.filter((u) => u.status === "uploading").length);
const processingCount = computed(
  () => uploads.value.filter((u) => u.status === "processing").length,
);
const processedCount = computed(() => uploads.value.filter((u) => u.status === "processed").length);
const validatedCount = computed(() => uploads.value.filter((u) => u.status === "validated").length);
const errorCount = computed(() => uploads.value.filter((u) => u.status === "error").length);

function generateId(): string {
  return crypto.randomUUID();
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
  uploads.value = uploads.value.filter((u) => u.id !== id);
}

function clearCompleted() {
  uploads.value = uploads.value.filter(
    (u) => u.status !== "processed" && u.status !== "validated" && u.status !== "error",
  );
}

function selectUpload(upload: FileUpload) {
  if (upload.status !== "processed" && upload.status !== "validated") return;
  emit("photo-selected", upload);
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

    // Upload slot freed (now "processing"), pick up next pending
    processQueue();
  } catch (err) {
    pending.status = "error";
    pending.error = err instanceof Error ? err.message : "Upload failed";
    processQueue();
  }
}

async function processPhoto(upload: FileUpload) {
  // Step 1: Trigger processing (returns immediately with runId)
  const triggerResponse = await fetch(`${API_URL}/process-photo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ imageKey: upload.key }),
  });

  if (!triggerResponse.ok) {
    throw new Error("Failed to start processing");
  }

  const { runId } = await triggerResponse.json();
  upload.runId = runId;
  upload.processingStage = "queued";

  // Step 2: Poll for status updates
  while (true) {
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const statusResponse = await fetch(`${API_URL}/process-photo/${runId}/status`);
    if (!statusResponse.ok) {
      throw new Error("Failed to check processing status");
    }

    const statusData = await statusResponse.json();

    if (statusData.stage === "error") {
      throw new Error(statusData.error || "Processing failed");
    }

    if (statusData.stage === "finalized") {
      upload.photoId = statusData.result.photoId;
      upload.result = {
        blurredUrl: statusData.result.blurredUrl,
        blurredKey: statusData.result.blurredKey,
        facesCount: statusData.result.facesCount,
        exif: statusData.result.exif,
        matchedEntrance: statusData.result.matchedEntrance,
      };
      if (statusData.result.status === "invalid") {
        upload.status = "error";
        upload.error = statusData.result.rejectionReason || "Photo invalide";
      } else {
        upload.status = "processed";
      }
      return;
    }

    // Update the granular processing stage
    upload.processingStage = statusData.stage;
  }
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
    <!-- Drop zone: full when empty, compact when uploads exist -->
    <template v-if="uploads.length === 0">
      <div class="flex-1 flex items-center justify-center p-8">
        <UploadDropZone @files-selected="addFiles" />
      </div>
    </template>
    <template v-else>
      <UploadDropZone compact @files-selected="addFiles" />

      <!-- Summary bar -->
      <div class="flex items-center justify-between px-4 py-2 border-b flex-shrink-0">
        <div class="flex gap-3 text-xs flex-wrap">
          <span v-if="pendingCount" class="text-muted-foreground">{{ pendingCount }} en attente</span>
          <span v-if="uploadingCount" class="text-primary font-medium"
            >{{ uploadingCount }} en cours d'envoi</span
          >
          <span v-if="processingCount" class="text-amber-600 font-medium"
            >{{ processingCount }} en traitement</span
          >
          <span v-if="processedCount" class="text-green-600">{{ processedCount }} terminé(s)</span>
          <span v-if="validatedCount" class="text-green-700 font-medium"
            >{{ validatedCount }} validée(s)</span
          >
          <span v-if="errorCount" class="text-destructive">{{ errorCount }} en erreur</span>
        </div>
        <button
          v-if="processedCount > 0 || validatedCount > 0 || errorCount > 0"
          class="text-xs text-muted-foreground hover:text-foreground transition-colors"
          @click="clearCompleted"
        >
          Effacer
        </button>
      </div>

      <!-- Upload grid -->
      <div class="flex-1 overflow-y-auto">
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 p-4 content-start">
          <div
            v-for="upload in uploads"
            :key="upload.id"
            class="relative rounded-lg overflow-hidden border shadow-sm bg-card aspect-square"
            :class="{
              'cursor-pointer hover:ring-2 hover:ring-primary/50': upload.status === 'processed',
              'cursor-pointer ring-2 ring-green-500/50': upload.status === 'validated',
            }"
            @click="selectUpload(upload)"
          >
            <!-- Processed or Validated: show blurred image -->
            <template
              v-if="
                (upload.status === 'processed' || upload.status === 'validated') && upload.result
              "
            >
              <img
                :src="upload.result.blurredUrl"
                :alt="upload.file.name"
                class="w-full h-full object-cover"
              />
              <!-- Validated overlay -->
              <div
                v-if="upload.status === 'validated'"
                class="absolute inset-0 bg-green-500/15 flex items-end justify-end p-1.5"
              >
                <div
                  class="w-6 h-6 rounded-full bg-green-600 flex items-center justify-center shadow"
                >
                  <Check class="w-3.5 h-3.5 text-white" />
                </div>
              </div>
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
                  <MapPin
                    v-if="upload.processingStage === 'analyzing_location'"
                    class="w-5 h-5 text-amber-600 animate-pulse"
                  />
                  <ShieldCheck
                    v-else-if="upload.processingStage === 'blurring_faces'"
                    class="w-5 h-5 text-amber-600 animate-pulse"
                  />
                  <ScanEye
                    v-else-if="upload.processingStage === 'validating_content'"
                    class="w-5 h-5 text-amber-600 animate-pulse"
                  />
                  <CheckCircle2
                    v-else-if="upload.processingStage === 'finalizing'"
                    class="w-5 h-5 text-amber-600 animate-pulse"
                  />
                  <div
                    v-else
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
                  En attente
                </p>
                <p v-else-if="upload.status === 'uploading'" class="text-xs text-primary">
                  {{ upload.progress }}%
                </p>
                <p v-else-if="upload.status === 'processing'" class="text-xs text-amber-600">
                  <template v-if="upload.processingStage === 'analyzing_location'"
                    >Analyse de la position...</template
                  >
                  <template v-else-if="upload.processingStage === 'blurring_faces'"
                    >Floutage des visages...</template
                  >
                  <template v-else-if="upload.processingStage === 'validating_content'"
                    >Vérification du contenu...</template
                  >
                  <template v-else-if="upload.processingStage === 'finalizing'"
                    >Finalisation...</template
                  >
                  <template v-else>Démarrage...</template>
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
