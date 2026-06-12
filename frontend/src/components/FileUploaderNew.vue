<template>
  <div class="upload-zone" @dragover.prevent @drop.prevent="onDrop">
    <input ref="input" type="file" :accept="acceptStr" hidden @change="onPick" />
    <div class="zone-content" @click="$refs.input.click()">
      <div class="zone-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      </div>
      <p class="zone-title">拖拽文件到此处，或点击上传</p>
      <p class="zone-hint">支持 PDF · DWG · PNG · JPG · Word · Excel</p>
      <p class="zone-limit">单个文件最大 100MB</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const emit = defineEmits(['uploaded'])
const input = ref(null)
const acceptStr = '.pdf,.dwg,.png,.jpg,.jpeg,.docx,.xlsx'
function onPick(e) { const f=e.target.files[0]; if(f) emit('uploaded',f) }
function onDrop(e) { const f=e.dataTransfer.files[0]; if(f) emit('uploaded',f) }
</script>

<style scoped>
.upload-zone {
  width:560px; height:340px; border:2px dashed #cbd5e1; border-radius:var(--radius-lg);
  cursor:pointer; transition:all var(--normal) var(--ease);
  display:flex; align-items:center; justify-content:center;
}
.upload-zone:hover { border-color:var(--brand); background:#f8faff; }
.zone-content { text-align:center; }
.zone-icon { color:#94a3b8; margin-bottom:16px; }
.zone-icon svg { display:block; margin:0 auto; }
.zone-title { font-size:16px; font-weight:600; color:var(--text-primary); margin-bottom:8px; }
.zone-hint { font-size:13px; color:var(--text-secondary); margin-bottom:4px; }
.zone-limit { font-size:11px; color:var(--text-tertiary); }
</style>
