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
    ElMessage.success(`成功上传 ${data.uploaded} 个印章${data.failed ? `，${data.failed} 个失败` :
``` (1/2)
