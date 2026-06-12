<template>
  <div class="canvas-workspace">
    <!-- Toolbar -->
    <div class="canvas-toolbar">
      <el-button @click="$emit('back')" :icon="'Back'">返回</el-button>
      <span class="file-name">{{ file.name }}</span>
      <el-select
        v-model="outputFormat"
        size="small"
        style="width: 100px"
      >
        <el-option label="PDF" value="pdf" />
        <el-option label="DWF" value="dwf" />
      </el-select>
      <el-button
        type="primary"
        @click="doStamp"
        :loading="stamping"
        :disabled="!stampPositions.length"
      >
        盖章 ({{ stampPositions.length }})
      </el-button>
    </div>

    <!-- Canvas -->
    <div class="canvas-container" ref="containerRef">
      <canvas ref="canvasRef" id="stamp-canvas"></canvas>
    </div>

    <!-- Position Table -->
    <div v-if="stampPositions.length" class="position-table">
      <el-table :data="stampPositions" size="small" max-height="150">
        <el-table-column label="印章" prop="sealName" width="100" />
        <el-table-column label="页码" prop="page" width="60" />
        <el-table-column label="X(mm)" prop="x_mm" width="80">
          <template #default="{ row }">
            <el-input-number
              v-model="row.x_mm"
              size="small"
              :min="0"
              :step="1"
              controls-position="right"
              @change="updatePosition(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="Y(mm)" prop="y_mm" width="80">
          <template #default="{ row }">
            <el-input-number
              v-model="row.y_mm"
              size="small"
              :min="0"
              :step="1"
              controls-position="right"
              @change="updatePosition(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="旋转" prop="rotation" width="80">
          <template #default="{ row }">
            <el-input-number
              v-model="row.rotation"
              size="small"
              :min="0"
              :max="360"
              :step="15"
              controls-position="right"
              @change="updatePosition(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ row }">
            <el-button type="danger" size="small" @click="removeStamp(row)">×</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as fabric from 'fabric'
import * as pdfjsLib from 'pdfjs-dist'
import { stampFile, getSealImageUrl } from '../api/index.js'

// Configure pdf.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`

const props = defineProps({
  file: { type: File, required: true },
  selectedSeal: { type: Object, default: null },
  stamping: { type: Boolean, default: false },
})

const emit = defineEmits(['back', 'stamp'])

const containerRef = ref(null)
const canvasRef = ref(null)
const outputFormat = ref('pdf')
const stampPositions = ref([])

let canvas = null
let bgImage = null

// ── Init Fabric Canvas ────────────────────────────────────

onMounted(async () => {
  await nextTick()

  const container = containerRef.value
  canvas = new fabric.Canvas(canvasRef.value, {
    width: container.clientWidth,
    height: container.clientHeight - 40,
    backgroundColor: '#fff',
  })

  // Load file as background
  const url = URL.createObjectURL(props.file)
  const ext = props.file.name.split('.').pop().toLowerCase()

  if (ext === 'pdf') {
    // For PDF: render first page as image via backend
    bgImage = await loadPdfPreview(props.file)
  } else {
    // For DWG/DWF: just show a placeholder (can't render in browser)
    bgImage = await createPlaceholder('DWG 文件预览\n盖章坐标将在服务端精确应用')
  }

  if (bgImage) {
    canvas.setDimensions({ width: bgImage.width, height: bgImage.height })
    canvas.add(bgImage)
    canvas.renderAll()
  }

  // Handle drop from seal library
  canvas.on('drop', onCanvasDrop)
  canvas.on('dragover', (e) => e.e.preventDefault())

  // Handle window resize
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  canvas?.dispose()
  window.removeEventListener('resize', onResize)
})

// ── Seal drop on canvas ──────────────────────────────────

watch(() => props.selectedSeal, (seal) => {
  if (!seal || !canvas) return
  addSealToCanvas(seal, canvas.width / 2, canvas.height / 2)
})

function onCanvasDrop(e) {
  e.e.preventDefault()
  const sealId = e.e.dataTransfer.getData('application/seal-id')
  const w = parseFloat(e.e.dataTransfer.getData('application/seal-width')) || 40
  const h = parseFloat(e.e.dataTransfer.getData('application/seal-height')) || 40
  if (!sealId) return

  const pointer = canvas.getPointer(e.e)
  addSealToCanvas({ id: sealId, default_width_mm: w, default_height_mm: h }, pointer.x, pointer.y)
}

function addSealToCanvas(seal, x, y) {
  const imgUrl = getSealImageUrl(seal.id)
  fabric.FabricImage.fromURL(imgUrl, { crossOrigin: 'anonymous' }).then((img) => {
    // Scale seal to approximate mm→px (assume 96 DPI for screen)
    const pxPerMm = 96 / 25.4
    const wPx = seal.default_width_mm * pxPerMm
    const hPx = seal.default_height_mm * pxPerMm
    img.scaleToWidth(wPx)

    img.set({
      left: x - wPx / 2,
      top: y - hPx / 2,
      hasControls: true,
      hasBorders: true,
      lockUniScaling: true,
    })

    canvas.add(img)
    canvas.setActiveObject(img)
    canvas.renderAll()

    // Track position
    const posEntry = {
      id: Date.now(),
      sealId: seal.id,
      sealName: seal.name || seal.id,
      page: 1,
      x_mm: 0,
      y_mm: 0,
      rotation: 0,
      fabricObject: img,
    }
    stampPositions.value.push(posEntry)

    // Bind change events
    img.on('modified', () => updatePosition(posEntry))
    updatePosition(posEntry)
  })
}

// ── Position sync (canvas ↔ data) ───────────────────────

function updatePosition(entry) {
  if (!entry.fabricObject || !canvas) return
  const obj = entry.fabricObject
  const pxPerMm = 96 / 25.4

  // Canvas px → mm (relative to top-left of canvas)
  entry.x_mm = Math.round(obj.left / pxPerMm * 10) / 10
  entry.y_mm = Math.round(obj.top / pxPerMm * 10) / 10
  entry.rotation = Math.round(obj.angle || 0)
}

function removeStamp(entry) {
  if (entry.fabricObject) {
    canvas.remove(entry.fabricObject)
    canvas.renderAll()
  }
  stampPositions.value = stampPositions.value.filter(p => p.id !== entry.id)
}

// ── Stamp action ─────────────────────────────────────────

async function doStamp() {
  if (!stampPositions.value.length) return

  const fd = new FormData()
  fd.append('file', props.file)
  fd.append('seal_id', stampPositions.value[0].sealId)
  fd.append('output_format', outputFormat.value)

  const positions = stampPositions.value.map(p => ({
    page: p.page,
    x_mm: p.x_mm,
    y_mm: p.y_mm,
    rotation: p.rotation,
    scale: 1.0,
  }))
  fd.append('positions_json', JSON.stringify(positions))

  try {
    emit('stamp', { stamping: true })
    const res = await stampFile(fd)
    const blob = res.data
    const ext = outputFormat.value
    const filename = `stamped_${props.file.name.replace(/\.[^.]+$/, '')}.${ext}`
    emit('stamp', { blob, filename })
  } catch (e) {
    ElMessage.error('盖章失败: ' + (e.response?.data?.detail || e.message))
    emit('stamp', { stamping: false })
  }
}

// ── Helpers ──────────────────────────────────────────────

async function loadPdfPreview(file) {
  /** Render first page via server-side preview API (PyMuPDF). */
  const fd = new FormData()
  fd.append('file', file)
  fd.append('page', '1')
  try {
    const res = await fetch('/api/v1/preview', { method: 'POST', body: fd })
    if (!res.ok) throw new Error('Preview failed')
    const blob = await res.blob()
    const dataUrl = URL.createObjectURL(blob)
    return new Promise((resolve) => {
      fabric.FabricImage.fromURL(dataUrl, (img) => {
        img.set({ selectable: false, evented: false })
        resolve(img)
      })
    })
  } catch {
    // Fallback to pdf.js if server preview unavailable
    return loadPdfPreviewPdfJs(file)
  }
}

async function loadPdfPreviewPdfJs(file) {
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  const page = await pdf.getPage(1)
  const viewport = page.getViewport({ scale: 1.5 })
  const offCanvas = document.createElement('canvas')
  offCanvas.width = viewport.width
  offCanvas.height = viewport.height
  const ctx = offCanvas.getContext('2d')
  await page.render({ canvasContext: ctx, viewport }).promise
  return new Promise((resolve) => {
    fabric.FabricImage.fromURL(offCanvas.toDataURL(), (img) => {
      img.set({ selectable: false, evented: false })
      resolve(img)
    })
  })
}

async function createPlaceholder(text) {
  /** Fallback placeholder for non-PDF files (e.g., DWG). */
  return new Promise((resolve) => {
    const bg = new fabric.Rect({
      width: 800, height: 600,
      fill: '#fafafa',
      rx: 8, ry: 8,
    })
    const textEl = new fabric.Text(text, {
      fontSize: 18,
      fill: '#999',
      textAlign: 'center',
      originX: 'center',
      originY: 'center',
    })
    const group = new fabric.Group([bg, textEl], {
      left: 0, top: 0,
      selectable: false, evented: false,
    })
    resolve(group)
  })
}

function onResize() {
  if (!canvas || !containerRef.value) return
  canvas.setDimensions({
    width: containerRef.value.clientWidth,
    height: containerRef.value.clientHeight - 40,
  })
  canvas.renderAll()
}
</script>

<style scoped>
.canvas-workspace {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.canvas-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.file-name {
  flex: 1;
  font-size: 14px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-container {
  flex: 1;
  overflow: auto;
  background: #ddd;
  display: flex;
  justify-content: center;
}
#stamp-canvas {
  box-shadow: 0 2px 12px rgba(0,0,0,.15);
}

.position-table {
  flex-shrink: 0;
  max-height: 160px;
  overflow: auto;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}
</style>
