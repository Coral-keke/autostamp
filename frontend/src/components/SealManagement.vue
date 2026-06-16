<template>
  <div class="seal-mgmt">
    <div class="mgmt-header">
      <div>
        <h2>印章管理</h2>
        <p>管理系统中的所有印章，支持上传、编辑、删除</p>
      </div>
      <button class="btn-upload" @click="openUpload">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        上传印章
      </button>
    </div>

    <!-- Upload modal -->
    <div class="modal-overlay" v-if="showUpload" @click.self="showUpload=false">
      <div class="modal-card">
        <h3>批量上传印章</h3>
        <div class="upload-dropzone" @click="$refs.uploadInput.click()" @dragover.prevent @drop.prevent="onDropFiles">
          <input ref="uploadInput" type="file" accept="image/png,image/jpeg" multiple hidden @change="onPickFiles" />
          <template v-if="!uploadFiles.length">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            <p>拖拽或点击上传多个 PNG 印章图片</p>
            <span>建议透明背景，500×500px · 支持批量选择</span>
          </template>
        </div>
        <!-- File list -->
        <div class="file-list" v-if="uploadFiles.length">
          <div class="file-item" v-for="(f, idx) in uploadFiles" :key="idx">
            <img :src="previews[idx]" class="file-thumb" />
            <div class="file-info">
              <span class="file-name">{{ f.name }}</span>
              <span class="file-size">{{ formatSize(f.size) }}</span>
            </div>
            <button class="file-remove" @click="removeFile(idx)">✕</button>
          </div>
        </div>
        <div class="batch-summary" v-if="uploadFiles.length">
          共 {{ uploadFiles.length }} 个文件
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showUpload=false">取消</button>
          <button class="btn-confirm" :disabled="!uploadFiles.length" @click="confirmBatchUpload">
            {{ uploading ? '上传中...' : `批量上传 (${uploadFiles.length})` }}
          </button>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="table-wrap">
      <table>
        <thead><tr><th>印章</th><th>名称</th><th>编码</th><th>尺寸</th><th>上传时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="s in seals" :key="s.id">
            <td><img :src="getSealImageUrl(s.id)" class="tb-thumb" /></td>
            <td><strong>{{ s.name }}</strong></td>
            <td><code>{{ s.seal_code }}</code></td>
            <td>{{ s.default_width_mm }}×{{ s.default_height_mm }}mm</td>
            <td>{{ formatDate(s.created_at) }}</td>
            <td>
              <button class="tb-del" @click="$emit('delete',s.id)">删除</button>
            </td>
          </tr>
          <tr v-if="!seals.length"><td colspan="6" class="empty-row">暂无印章，点击右上角上传</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSealImageUrl, uploadSealsBatch } from '../api/index.js'

defineProps({ seals:{type:Array,default:()=>[]} })
const emit = defineEmits(['upload','delete','refresh'])
const showUpload = ref(false)
const uploadFiles = ref([])
const previews = ref([])
const uploading = ref(false)

function openUpload(){ showUpload.value=true; uploadFiles.value=[]; previews.value=[] }

function onPickFiles(e){
  const files = Array.from(e.target.files)
  addFiles(files)
}

function onDropFiles(e){
  const files = Array.from(e.dataTransfer.files)
  addFiles(files)
}

function addFiles(files){
  for(const f of files){
    if(!f.type.match(/image\/(png|jpeg)/)) continue
    uploadFiles.value.push(f)
    previews.value.push(URL.createObjectURL(f))
  }
}

function removeFile(idx){
  uploadFiles.value.splice(idx,1)
  previews.value.splice(idx,1)
}

async function confirmBatchUpload(){
  if(!uploadFiles.value.length) return
  uploading.value = true
  const fd = new FormData()
  for(const f of uploadFiles.value){
    fd.append('files', f)
  }
  try {
    const res = await uploadSealsBatch(fd)
    const data = res.data
    ElMessage.success(`成功上传 ${data.uploaded} 个印章${data.failed ? `，${data.failed} 个失败` : ''}`)
    if(data.errors.length){
      console.warn('上传失败:', data.errors)
    }
    emit('refresh')
    showUpload.value = false
  } catch(e){
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

function formatSize(bytes){
  if(bytes<1024) return bytes+'B'
  if(bytes<1048576) return (bytes/1024).toFixed(1)+'KB'
  return (bytes/1048576).toFixed(1)+'MB'
}
function formatDate(s){ if(!s) return '-'; try{ return new Date(s).toLocaleDateString('zh-CN') }catch{ return s.slice(0,10) } }
</script>

<style scoped>
.seal-mgmt { padding:32px 40px; overflow-y:auto; height:100%; }
.mgmt-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:24px; }
.mgmt-header h2 { font-size:22px; font-weight:700; color:var(--text-primary); }
.mgmt-header p { font-size:13px; color:var(--text-secondary); margin-top:4px; }
.btn-upload { display:flex; align-items:center; gap:6px; padding:8px 20px; border:none; background:var(--brand); color:#fff; border-radius:var(--radius-md); font-size:13px; font-weight:600; cursor:pointer; transition:all var(--fast) var(--ease); }
.btn-upload:hover { background:var(--brand-dark); }

.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.35); z-index:100; display:flex; align-items:center; justify-content:center; }
.modal-card { background:#fff; border-radius:var(--radius-lg); padding:28px; width:440px; box-shadow:var(--shadow-xl); }
.modal-card h3 { font-size:16px; font-weight:700; margin-bottom:16px; }
.upload-dropzone { border:2px dashed var(--border); border-radius:var(--radius-md); padding:32px; text-align:center; cursor:pointer; transition:all var(--fast); margin-bottom:16px; }
.upload-dropzone:hover { border-color:var(--brand); background:#f8faff; }
.upload-dropzone p { font-size:13px; color:var(--text-secondary); margin-top:8px; }
.upload-dropzone span { font-size:11px; color:var(--text-tertiary); }

.file-list { max-height:220px; overflow-y:auto; margin-bottom:12px; }
.file-item { display:flex; align-items:center; gap:10px; padding:8px 10px; border:1px solid var(--border-light); border-radius:var(--radius-sm); margin-bottom:6px; }
.file-thumb { width:36px; height:36px; border-radius:4px; object-fit:contain; border:1px solid var(--border); }
.file-info { flex:1; min-width:0; }
.file-name { display:block; font-size:12px; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.file-size { font-size:11px; color:var(--text-tertiary); }
.file-remove { border:none; background:none; color:var(--text-tertiary); cursor:pointer; font-size:14px; padding:4px; border-radius:50%; transition:all var(--fast); }
.file-remove:hover { background:#fee2e2; color:var(--danger); }
.batch-summary { font-size:12px; color:var(--text-secondary); margin-bottom:16px; text-align:center; }
.field { padding:8px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-size:13px; outline:none; }
.field:focus { border-color:var(--brand); }
.modal-actions { display:flex; gap:10px; justify-content:flex-end; }
.btn-cancel { padding:8px 20px; border:1px solid var(--border); background:#fff; border-radius:var(--radius-sm); font-size:13px; cursor:pointer; }
.btn-confirm { padding:8px 20px; border:none; background:var(--brand); color:#fff; border-radius:var(--radius-sm); font-size:13px; font-weight:600; cursor:pointer; }
.btn-confirm:disabled { opacity:.4; cursor:not-allowed; }

.table-wrap { background:#fff; border-radius:var(--radius-md); border:1px solid var(--border); overflow:hidden; }
table { width:100%; border-collapse:collapse; }
th { text-align:left; padding:12px 16px; font-size:11px; font-weight:600; color:var(--text-tertiary); text-transform:uppercase; letter-spacing:.5px; border-bottom:1px solid var(--border); background:var(--bg-page); }
td { padding:14px 16px; font-size:13px; border-bottom:1px solid var(--border-light); }
td code { font-size:12px; background:var(--bg-page); padding:2px 6px; border-radius:3px; color:var(--brand); font-family:var(--font-mono); }
.tb-thumb { width:36px; height:36px; border-radius:4px; object-fit:contain; border:1px solid var(--border); }
.tb-del { padding:4px 12px; border:1px solid #fecaca; background:#fef2f2; color:var(--danger); border-radius:var(--radius-sm); font-size:11px; cursor:pointer; transition:all var(--fast); }
.tb-del:hover { background:#fee2e2; }
.empty-row { text-align:center; color:var(--text-tertiary); padding:48px 0; }
</style>
