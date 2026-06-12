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
        <h3>上传印章</h3>
        <div class="upload-dropzone" @click="$refs.uploadInput.click()" @dragover.prevent @drop.prevent="onDropFile">
          <input ref="uploadInput" type="file" accept="image/png,image/jpeg" hidden @change="onPickFile" />
          <template v-if="!uploadFile">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            <p>拖拽或点击上传 PNG 印章图片</p>
            <span>建议透明背景，500×500px</span>
          </template>
          <template v-else>
            <img :src="uploadPreview" class="preview" />
          </template>
        </div>
        <div class="form-grid" v-if="uploadFile">
          <input v-model="form.name" class="field" placeholder="印章名称" />
          <input v-model="form.sealCode" class="field" placeholder="编码 (如 VP_GZ_001)" />
          <input v-model.number="form.width" class="field" type="number" placeholder="宽 mm" />
          <input v-model.number="form.height" class="field" type="number" placeholder="高 mm" />
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showUpload=false">取消</button>
          <button class="btn-confirm" :disabled="!uploadFile" @click="confirmUpload">确认上传</button>
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
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { getSealImageUrl } from '../api/index.js'

defineProps({ seals:{type:Array,default:()=>[]} })
const emit = defineEmits(['upload','delete','refresh'])
const showUpload = ref(false); const uploadFile = ref(null); const uploadPreview = ref('')
const form = reactive({ name:'',sealCode:'',width:40,height:40 })
function openUpload(){ showUpload.value=true; uploadFile.value=null; uploadPreview.value=''; form.name=''; form.sealCode=''; form.width=40; form.height=40 }
function onPickFile(e){ const f=e.target.files[0]; if(f){ uploadFile.value=f; uploadPreview.value=URL.createObjectURL(f); form.name=f.name.replace(/\.[^.]+$/,'') } }
function onDropFile(e){ const f=e.dataTransfer.files[0]; if(f){ uploadFile.value=f; uploadPreview.value=URL.createObjectURL(f); form.name=f.name.replace(/\.[^.]+$/,'') } }
function confirmUpload(){
  if(!uploadFile.value) return
  const fd=new FormData(); fd.append('file',uploadFile.value); fd.append('name',form.name); fd.append('seal_code',form.sealCode||'SEAL_'+Date.now()); fd.append('default_width_mm',form.width); fd.append('default_height_mm',form.height)
  emit('upload',fd); showUpload.value=false
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
.preview { max-width:150px; max-height:150px; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:20px; }
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
