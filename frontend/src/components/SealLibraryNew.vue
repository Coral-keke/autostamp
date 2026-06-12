<template>
  <div class="seal-panel">
    <div class="panel-header">
      <h3>印章库</h3>
      <button class="btn-upload" @click="$refs.fileInput.click()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        上传
      </button>
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/svg+xml" hidden @change="onFilePicked" />
    </div>

    <!-- Upload form -->
    <div v-if="uploading" class="upload-card">
      <div class="upload-preview">
        <img v-if="previewUrl" :src="previewUrl" alt="preview" />
      </div>
      <input v-model="form.name" class="field" placeholder="印章名称" />
      <input v-model="form.sealCode" class="field" placeholder="印章编码 (如 VP_GZ_001)" />
      <div class="row">
        <input v-model.number="form.width" class="field half" type="number" placeholder="宽 mm" />
        <input v-model.number="form.height" class="field half" type="number" placeholder="高 mm" />
      </div>
      <div class="btn-group">
        <button class="btn-cancel" @click="cancelUpload">取消</button>
        <button class="btn-confirm" @click="doUpload">确认上传</button>
      </div>
    </div>

    <!-- Seal grid -->
    <div class="seal-grid" v-if="seals.length">
      <div
        v-for="seal in seals" :key="seal.id"
        class="seal-card" :class="{selected: selectedId===seal.id}"
        draggable="true"
        @dragstart="onDrag(seal,$event)"
        @click="$emit('select',seal)"
      >
        <div class="card-img">
          <img :src="imageUrl(seal.id)" :alt="seal.name" />
        </div>
        <div class="card-body">
          <span class="card-name">{{ seal.name }}</span>
          <span class="card-code">{{ seal.seal_code }}</span>
        </div>
        <button class="card-del" @click.stop="$emit('delete',seal.id)" title="删除">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
        </button>
      </div>
    </div>

    <div v-else class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.2"><circle cx="12" cy="13" r="7"/><path d="M12 2v4M12 20v2M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 13h4M18 13h4"/></svg>
      <p>暂无印章</p>
      <span>点击「上传」添加印章</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { getSealImageUrl } from '../api/index.js'

const props = defineProps({ seals:{type:Array,default:()=>[]}, selectedId:String })
const emit = defineEmits(['upload','delete','select','refresh'])
const fileInput = ref(null)
const uploading = ref(false)
const previewUrl = ref('')
const form = reactive({ name:'', sealCode:'', width:40, height:40, file:null })

function imageUrl(id) { return getSealImageUrl(id) }
function onDrag(seal, e) {
  e.dataTransfer.setData('application/seal-id', seal.id)
  e.dataTransfer.setData('application/seal-width', seal.default_width_mm)
  e.dataTransfer.setData('application/seal-height', seal.default_height_mm)
  e.dataTransfer.effectAllowed = 'copy'
}
function onFilePicked(e) {
  const f = e.target.files[0]; if(!f) return
  form.file = f; form.name = f.name.replace(/\.[^.]+$/,'')
  previewUrl.value = URL.createObjectURL(f); uploading.value = true
}
function cancelUpload() { uploading.value = false; form.file = null; previewUrl.value=''; if(fileInput.value) fileInput.value.value='' }
function doUpload() {
  if(!form.file) return
  const fd = new FormData(); fd.append('file',form.file); fd.append('name',form.name)
  fd.append('seal_code',form.sealCode||'SEAL_'+Date.now()); fd.append('default_width_mm',form.width); fd.append('default_height_mm',form.height)
  emit('upload',fd); cancelUpload()
}
</script>

<style scoped>
.seal-panel { display:flex; flex-direction:column; height:100%; }
.panel-header { display:flex; align-items:center; justify-content:space-between; padding:16px 16px 12px; }
.panel-header h3 { font-size:14px; font-weight:600; color:var(--text-primary); }
.btn-upload {
  display:flex; align-items:center; gap:4px; padding:6px 14px;
  border:1px solid var(--brand); background:var(--brand-bg); color:var(--brand);
  border-radius:var(--radius-sm); font-size:12px; font-weight:600; cursor:pointer;
  transition:all var(--fast) var(--ease);
}
.btn-upload:hover { background:var(--brand); color:#fff; }

.upload-card { padding:12px 16px; border-bottom:1px solid var(--border); display:flex; flex-direction:column; gap:8px; }
.upload-preview { width:100%; height:80px; background:var(--bg-page); border-radius:var(--radius-sm); display:flex; align-items:center; justify-content:center; overflow:hidden; }
.upload-preview img { max-width:100%; max-height:100%; object-fit:contain; }
.field { width:100%; padding:7px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-size:12px; font-family:var(--font-sans); outline:none; transition:border var(--fast); }
.field:focus { border-color:var(--brand); }
.field.half { width:calc(50% - 4px); }
.row { display:flex; gap:8px; }
.btn-group { display:flex; gap:8px; justify-content:flex-end; }
.btn-cancel { padding:6px 16px; border:1px solid var(--border); background:#fff; border-radius:var(--radius-sm); font-size:12px; cursor:pointer; }
.btn-confirm { padding:6px 16px; border:none; background:var(--brand); color:#fff; border-radius:var(--radius-sm); font-size:12px; font-weight:600; cursor:pointer; }

.seal-grid { padding:12px; display:grid; grid-template-columns:1fr 1fr; gap:10px; overflow-y:auto; }
.seal-card {
  background:var(--bg-surface); border:1.5px solid var(--border); border-radius:var(--radius-md);
  padding:10px; cursor:pointer; position:relative; transition:all var(--fast) var(--ease);
}
.seal-card:hover { border-color:#93c5fd; box-shadow:var(--shadow-sm); }
.seal-card.selected { border-color:var(--brand); background:var(--brand-bg); }
.card-img { height:60px; display:flex; align-items:center; justify-content:center; margin-bottom:6px; }
.card-img img { max-width:100%; max-height:60px; object-fit:contain; }
.card-body { text-align:center; }
.card-name { display:block; font-size:11px; font-weight:600; color:var(--text-primary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.card-code { display:block; font-size:10px; color:var(--text-tertiary); margin-top:2px; font-family:var(--font-mono); }
.card-del {
  position:absolute; top:4px; right:4px; width:24px; height:24px;
  border:none; background:transparent; color:var(--text-tertiary); border-radius:var(--radius-sm);
  cursor:pointer; display:flex; align-items:center; justify-content:center; opacity:0; transition:all var(--fast);
}
.seal-card:hover .card-del { opacity:1; }
.card-del:hover { background:#fef2f2; color:var(--danger); }

.empty-state { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; color:var(--text-tertiary); }
.empty-state p { font-size:14px; font-weight:500; color:var(--text-secondary); }
.empty-state span { font-size:12px; }
</style>
