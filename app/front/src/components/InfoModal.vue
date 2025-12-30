<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click="close">
        <div class="modal-content" @click.stop>
          <button class="close-button" aria-label="Close" @click="close">×</button>

          <h2>What is this?</h2>

          <div class="modal-body">
            <p>
              <i>"Metro, Boulot, Photos!"</i> is a project to document photos of all metro entrances
              in Paris. This interactive map shows every metro station and entrance, with their
              exact locations and the lines they serve.
            </p>

            <p>
              The metro data is compiled from
              <a href="https://data.iledefrance-mobilites.fr"
                >IDFM (Île-de-France Mobilités) open datasets</a
              >, providing accurate information about Paris metro stations, their entrances, and
              line associations.
            </p>

            <p>
              The photos come from myself, and from <b>you</b>! I will soon allow uploading pictures
              so you can participate in building this mosaïque of our beloved city.
            </p>

            <ul>
              <li>
                <b>Click</b> on any entrance marker to highlight all entrances that share the same
                metro lines.
              </li>
              <li><b>Hover</b> over markers to see station and entrance details.</li>
            </ul>

            <div class="links">
              <a
                href="https://github.com/ybadiss/metro-photos"
                target="_blank"
                rel="noopener noreferrer"
                class="link-button"
              >
                <svg
                  class="icon"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
                  />
                </svg>
                <span>GitHub</span>
              </a>

              <a
                href="https://badyass.xyz"
                target="_blank"
                rel="noopener noreferrer"
                class="link-button"
              >
                <svg
                  class="icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
                <span>About me</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
interface Props {
  isOpen: boolean
}

interface Emits {
  (e: 'close'): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

function close() {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 32px;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.close-button {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  font-size: 32px;
  cursor: pointer;
  color: #666;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.close-button:hover {
  background-color: #f0f0f0;
  color: #333;
}

h2 {
  margin: 0 0 24px 0;
  font-size: 28px;
  font-weight: 700;
  color: #333;
}

.modal-body p {
  margin: 0 0 16px 0;
  line-height: 1.6;
  color: #555;
}

.modal-body a {
  color: #0066cc;
  text-decoration: none;
  font-weight: 500;
}

.modal-body a:hover {
  text-decoration: underline;
}

.modal-body ul {
  margin: 20px 0;
  padding-left: 0;
  list-style: none;
}

.modal-body ul li {
  margin: 12px 0;
  padding-left: 28px;
  position: relative;
  line-height: 1.6;
  color: #555;
}

.modal-body ul li::before {
  content: '→';
  position: absolute;
  left: 0;
  color: #333;
  font-weight: bold;
  font-size: 18px;
}

.modal-body ul li b {
  color: #333;
  font-weight: 600;
}

.links {
  display: flex;
  gap: 12px;
  margin-top: 32px;
  flex-wrap: wrap;
}

.link-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background-color: #f5f5f5;
  border-radius: 8px;
  text-decoration: none;
  color: #333;
  font-weight: 500;
  transition: all 0.2s;
  flex: 1;
  min-width: 150px;
  justify-content: center;
}

.link-button:hover {
  background-color: #e0e0e0;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.icon {
  width: 20px;
  height: 20px;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .modal-content,
.modal-leave-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.9);
}
</style>
