<template>
  <LoginPage v-if="!authenticated" @authenticated="onAuth" />
  <div class="app-shell" v-else>
    <!-- ── Sidebar ──────────────────────────── -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="13" r="3.5" stroke="currentColor" stroke-width="1.5"/><path d="M8 8h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </div>
        <span class="brand-name">AutoStamp</span>
        <span class="brand-ver">v2.0</span>
      </div>

      <nav class="sidebar-nav">
        <button :class="{active: view==='stamp'}" @click="view='stamp'">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="13" r="7"/><path d="M12 2v4M12 20v2M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 13h4M18 13h4"/></svg>
          盖章工作台
        </button>
        <button :class="{active: view==='seals'}" @click="view='seals'">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M12 8v8M8 12h8"/></svg>
          印章管理
        </button>
        <button :class="{active: view==='api'}" @click="view='api'">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>
          API 文档
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="status-row">
          <span class="dot" :class="healthOk?'on':'off'"></span>
          <span>{{ healthOk ? '服务正常' : '离线' }}</span>
        </div>
        <span class="job-badge" v-if="health">队列 {{health.jobs?.processing||0}}</span>
      </div>
    </aside>

    <!-- ── Main Area ────────────────────────── -->
    <div class="main-area">
      <!-- View: Stamp Workspace -->
      <template v-if="view==='stamp'">
        <div class="workspace-layout">
          <div class="ws-left">
            <SealLibraryNew
              :seals="seals"
              :selected-id="selectedSeal?.id"
              @upload="handleSealUpload"
              @delete="handleSealDelete"
              @select="handleSealSelect"
              @refresh="refreshSeals"
            />
          </div>
          <div class="ws-center">
            <FileUploaderNew v-if="!currentFile" @uploaded="handleFileUploaded" />
            <StampCanvasNew
              v-else
              :file="currentFile"
              :selected-seal="selectedSeal"
              @back="handleReset"
              @stamp="handleStamp"
              :stamping="stamping"
            />
          </div>
        </div>
      </template>

      <!-- View: Seal Management -->
      <template v-if="view==='seals'">
        <SealManagement
          :seals="seals"
          @upload="handleSealUpload"
          @delete="handleSealDelete"
          @refresh="refreshSeals"
        />
      </template>

      <!-- View: API Docs -->
      <template v-if="view==='api'">
        <ApiReferenceNew />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import LoginPage from './components/LoginPage.vue'
import SealLibraryNew from './components/SealLibraryNew.vue'
import StampCanvasNew from './components/StampCanvasNew.vue'
import FileUploaderNew from './components/FileUploaderNew.vue'
import SealManagement from './components/SealManagement.vue'
import ApiReferenceNew from './components/ApiReferenceNew.vue'
import { listSeals, uploadSeal, deleteSeal } from './api/index.js'
import { ElMessage } from 'element-plus'

const view = ref('stamp')
const authenticated = ref(!!localStorage.getItem('stamp_token'))
const seals = ref([])
const selectedSeal = ref(null)
const currentFile = ref(null)
const stamping = ref(false)
const health = ref(null)
const healthOk = ref(false)
let healthTimer = null

onMounted(() => { refreshSeals(); checkHealth(); healthTimer = setInterval(checkHealth, 15000) })
onUnmounted(() => clearInterval(healthTimer))

async function checkHealth() {
  try { const r = await fetch('/api/v1/health'); health.value = await r.json(); healthOk.value = health.value?.status==='ok' }
  catch { healthOk.value = false }
}
async function refreshSeals() {
  try { const r = await listSeals(); seals.value = r.data.seals }
  catch { ElMessage.error('加载印章失败') }
}
async function handleSealUpload(fd) {
  try { await uploadSeal(fd); ElMessage.success('印章上传成功'); await refreshSeals() }
  catch(e) { ElMessage.error(e.response?.data?.detail||'上传失败') }
}
async function handleSealDelete(id) {
  try { await deleteSeal(id); ElMessage.success('已删除'); if(selectedSeal.value?.id===id) selectedSeal.value=null; await refreshSeals() }
  catch { ElMessage.error('删除失败') }
}
function handleSealSelect(s) { selectedSeal.value = s }
function onAuth() { authenticated.value = true }
function handleFileUploaded(f) { currentFile.value = f }
function handleReset() { currentFile.value = null; selectedSeal.value = null }
function handleStamp({blob,filename}) {
  const u = URL.createObjectURL(blob||new Blob()); const a=document.createElement('a'); a.href=u; a.download=filename||'stamped.pdf'; a.click(); URL.revokeObjectURL(u); ElMessage.success('盖章完成')
}
</script>

<style>
@import './design.css';

.app-shell { display:flex; height:100vh; overflow:hidden; }

/* ── Sidebar ─────────────────────────────────── */
.sidebar {
  width:240px; flex-shrink:0; background:var(--bg-surface);
  border-right:1px solid var(--border); display:flex; flex-direction:column;
}
.sidebar-brand { display:flex; align-items:center; gap:10px; padding:20px 20px 16px; border-bottom:1px solid var(--border); }
.brand-icon { color:var(--brand); }
.brand-name { font-size:17px; font-weight:700; color:var(--text-primary); letter-spacing:-.3px; }
.brand-ver { font-size:11px; color:var(--text-tertiary); background:var(--bg-page); padding:2px 6px; border-radius:var(--radius-sm); }

.sidebar-nav { flex:1; padding:12px; display:flex; flex-direction:column; gap:2px; }
.sidebar-nav button {
  display:flex; align-items:center; gap:10px; width:100%; padding:10px 12px;
  border:none; background:transparent; border-radius:var(--radius-md);
  font-size:13px; font-family:var(--font-sans); color:var(--text-secondary);
  cursor:pointer; transition:all var(--fast) var(--ease);
}
.sidebar-nav button:hover { background:var(--bg-hover); color:var(--text-primary); }
.sidebar-nav button.active { background:var(--brand-bg); color:var(--brand); font-weight:600; }

.sidebar-footer { padding:16px 20px; border-top:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; }
.status-row { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--text-secondary); }
.dot { width:7px; height:7px; border-radius:50%; }
.dot.on { background:var(--success); box-shadow:0 0 6px var(--success); }
.dot.off { background:var(--danger); }
.job-badge { font-size:11px; background:var(--brand-bg); color:var(--brand); padding:2px 8px; border-radius:var(--radius-full); }

/* ── Main ────────────────────────────────────── */
.main-area { flex:1; overflow:hidden; display:flex; flex-direction:column; background:var(--bg-page); }

.workspace-layout { flex:1; display:flex; overflow:hidden; }
.ws-left { width:300px; flex-shrink:0; border-right:1px solid var(--border); background:var(--bg-surface); overflow-y:auto; }
.ws-center { flex:1; display:flex; justify-content:center; align-items:center; overflow:hidden; }
</style>
