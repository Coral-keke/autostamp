<template>
  <div class="stamp-workspace">
    <!-- Toolbar -->
    <div class="toolbar">
      <button class="tb-btn ghost" @click="$emit('back')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
        返回
      </button>
      <span class="tb-file">{{ file.name }}</span>
      <div class="tb-right">
        <span class="badge" v-if="stampPositions.length">{{ stampPositions.length }} 枚印章</span>
        <select v-model="outputFormat" class="tb-select">
          <option value="pdf">输出 PDF</option>
          <option value="dwf">输出 DWF</option>
        </select>
        <button class="tb-btn primary" :disabled="!stampPositions.length||stamping" @click="doStamp">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="13" r="7"/><path d="M12 2v4M12 20v2"/></svg>
          {{ stamping?'处理中...':'盖章并下载' }}
        </button>
      </div>
    </div>

    <!-- Canvas -->
    <div class="canvas-viewport" ref="containerRef">
      <canvas ref="canvasRef"></canvas>
    </div>

    <!-- Position table -->
    <div v-if="stampPositions.length" class="pos-panel">
      <div class="pos-item" v-for="p in stampPositions" :key="p.id">
        <span class="pos-seal">{{ p.sealName }}</span>
        <span class="pos-coord">页{{ p.page }} · X:{{ p.x_mm }} Y:{{ p.y_mm }}mm</span>
        <button class="pos-del" @click="removeStamp(p)">×</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as fabric from 'fabric'
import { stampFile, getSealImageUrl } from '../api/index.js'

const props = defineProps({ file:{type:File,required:true}, selectedSeal:Object, stamping:Boolean })
const emit = defineEmits(['back','stamp'])
const containerRef = ref(null); const canvasRef = ref(null)
const outputFormat = ref('pdf'); const stampPositions = ref([])
let canvas = null

onMounted(async () => {
  await nextTick()
  canvas = new fabric.Canvas(canvasRef.value, {
    width:800, height:600, backgroundColor:'#fff',
  })
  const ext = props.file.name.split('.').pop().toLowerCase()
  if(ext==='pdf') { await loadPdfBg() }
  else { await loadPlaceholder() }
  canvas.on('drop',onDrop); canvas.on('dragover',e=>e.e.preventDefault())
})

onUnmounted(()=>canvas?.dispose())

watch(()=>props.selectedSeal, s=>{ if(s&&canvas) addSeal(s, canvas.width/2, canvas.height/2) })

async function loadPdfBg() {
  const fd = new FormData(); fd.append('file',props.file); fd.append('page','1')
  try {
    const r = await fetch('/api/v1/preview',{method:'POST',body:fd})
    if(r.ok){ const blob=await r.blob(); const url=URL.createObjectURL(blob)
      fabric.FabricImage.fromURL(url,i=>{ i.set({selectable:false,evented:false}); canvas.setDimensions({width:i.width,height:i.height}); canvas.add(i); canvas.renderAll() }) }
  }catch{ loadPlaceholder() }
}
async function loadPlaceholder() {
  const r=new fabric.Rect({width:800,height:600,fill:'#fafbfc',rx:8})
  const t=new fabric.Text('文件预览不可用\n盖章坐标将精确应用',{fontSize:15,fill:'#94a3b8',textAlign:'center',originX:'center',originY:'center'})
  canvas.add(new fabric.Group([r,t],{left:0,top:0,selectable:false,evented:false})); canvas.renderAll()
}

function onDrop(e) {
  e.e.preventDefault()
  const sealId=e.e.dataTransfer.getData('application/seal-id')
  const w=parseFloat(e.e.dataTransfer.getData('application/seal-width'))||40
  const h=parseFloat(e.e.dataTransfer.getData('application/seal-height'))||40
  if(!sealId) return
  const p=canvas.getPointer(e.e); addSeal({id:sealId,default_width_mm:w,default_height_mm:h,name:''},p.x,p.y)
}
function addSeal(seal,x,y) {
  fabric.FabricImage.fromURL(getSealImageUrl(seal.id),{crossOrigin:'anonymous'}).then(img=>{
    const ppm=96/25.4; const w=seal.default_width_mm*ppm
    img.scaleToWidth(w); img.set({left:x-w/2,top:y-seal.default_height_mm*ppm/2,hasControls:true,lockUniScaling:true})
    canvas.add(img); canvas.setActiveObject(img); canvas.renderAll()
    const e={id:Date.now(),sealId:seal.id,sealName:seal.name||'印章',page:1,x_mm:0,y_mm:0,rotation:0,fabricObject:img}
    img.on('modified',()=>{ const ppm=96/25.4; e.x_mm=Math.round(img.left/ppm*10)/10; e.y_mm=Math.round(img.top/ppm*10)/10; e.rotation=Math.round(img.angle||0) })
    stampPositions.value.push(e)
  })
}
function removeStamp(e) { if(e.fabricObject){canvas.remove(e.fabricObject);canvas.renderAll()} stampPositions.value=stampPositions.value.filter(p=>p.id!==e.id) }

async function doStamp() {
  if(!stampPositions.value.length) return
  const fd=new FormData(); fd.append('file',props.file); fd.append('seal_id',stampPositions.value[0].sealId)
  fd.append('output_format',outputFormat.value); fd.append('positions_json',JSON.stringify(stampPositions.value.map(p=>({page:p.page,x_mm:p.x_mm,y_mm:p.y_mm,rotation:p.rotation,scale:1.0}))))
  try{
    const r=await stampFile(fd); const blob=r.data
    emit('stamp',{blob,filename:`stamped_${props.file.name.replace(/\.[^.]+$/,'')}.${outputFormat.value}`})
  }catch(e){ ElMessage.error('盖章失败:'+(e.response?.data?.detail||e.message)) }
}
</script>

<style scoped>
.stamp-workspace { width:100%; height:100%; display:flex; flex-direction:column; }
.toolbar { display:flex; align-items:center; gap:12px; padding:12px 20px; background:var(--bg-surface); border-bottom:1px solid var(--border); flex-shrink:0; }
.tb-file { flex:1; font-size:13px; font-weight:500; color:var(--text-primary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.tb-right { display:flex; align-items:center; gap:8px; }
.tb-btn { display:flex; align-items:center; gap:6px; padding:7px 16px; border-radius:var(--radius-sm); font-size:12px; font-weight:600; cursor:pointer; transition:all var(--fast) var(--ease); font-family:var(--font-sans); }
.tb-btn.ghost { border:1px solid var(--border); background:#fff; color:var(--text-secondary); }
.tb-btn.ghost:hover { border-color:#cbd5e1; background:var(--bg-hover); }
.tb-btn.primary { border:none; background:var(--brand); color:#fff; }
.tb-btn.primary:hover:not(:disabled) { background:var(--brand-dark); }
.tb-btn:disabled { opacity:.5; cursor:not-allowed; }
.tb-select { padding:6px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-size:12px; background:#fff; font-family:var(--font-sans); }
.badge { font-size:11px; background:var(--brand-bg); color:var(--brand); padding:3px 10px; border-radius:var(--radius-full); font-weight:600; }

.canvas-viewport { flex:1; overflow:auto; background:#e8ecf1; display:flex; align-items:center; justify-content:center; padding:24px; }
.canvas-viewport canvas { box-shadow:var(--shadow-lg); }

.pos-panel { flex-shrink:0; border-top:1px solid var(--border); background:var(--bg-surface); padding:8px 20px; display:flex; gap:8px; overflow-x:auto; }
.pos-item { display:flex; align-items:center; gap:8px; padding:6px 12px; background:var(--bg-page); border-radius:var(--radius-sm); font-size:11px; white-space:nowrap; }
.pos-seal { font-weight:600; color:var(--text-primary); }
.pos-coord { color:var(--text-tertiary); font-family:var(--font-mono); }
.pos-del { border:none; background:transparent; color:var(--text-tertiary); cursor:pointer; font-size:16px; line-height:1; padding:0 2px; border-radius:3px; }
.pos-del:hover { color:var(--danger); background:#fef2f2; }
</style>
