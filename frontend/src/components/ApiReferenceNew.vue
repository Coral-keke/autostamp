<template>
  <div class="api-docs">
    <div class="docs-header">
      <h2>API 文档</h2>
      <p>外部系统调用接口说明 · 全部端点支持 JSON 交互</p>
    </div>

    <!-- Tabs -->
    <div class="doc-tabs">
      <button :class="{active:tab==='overview'}" @click="tab='overview'">概览</button>
      <button :class="{active:tab==='submit'}" @click="tab='submit'">提交盖章</button>
      <button :class="{active:tab==='status'}" @click="tab='status'">查询/下载</button>
      <button :class="{active:tab==='keywords'}" @click="tab='keywords'">关键字/骑缝</button>
      <button :class="{active:tab==='tester'}" @click="tab='tester'">🧪 在线测试</button>
    </div>

    <!-- ── Overview ─────────────────────────────── -->
    <div v-if="tab==='overview'" class="doc-body">
      <div class="endpoint-list">
        <div class="ep-row" v-for="ep in endpoints" :key="ep.method+ep.path">
          <span class="ep-method" :class="ep.method">{{ ep.method }}</span>
          <span class="ep-path">{{ ep.path }}</span>
          <span class="ep-desc">{{ ep.desc }}</span>
        </div>
      </div>
    </div>

    <!-- ── Submit ────────────────────────────────── -->
    <div v-if="tab==='submit'" class="doc-body">
      <div class="section">
        <h3>POST /api/v1/stamp/submit</h3>
        <p>异步提交盖章请求，立即返回 ACCEPTED，后台处理完成后回调。</p>
        <h4>请求体</h4>
        <pre class="code-block"><code>{
  "requestNo": "REQ-20260604-001",
  "businessId": "BIZ-123",
  "systemCode": "VP",
  "systemName": "可视化平台",
  "fileType": "pdf",
  "sealCode": "VP_GZ_001",
  "fileUrl": "https://your-system/contract.pdf",
  "callbackUrl": "https://your-system/api/callback",
  "position": {
    "x": 420, "y": 680,
    "width": 120, "height": 120,
    "page": 1, "rotation": 0
  }
}</code></pre>
        <h4>响应</h4>
        <pre class="code-block"><code>{
  "requestNo": "REQ-20260604-001",
  "status": "ACCEPTED",
  "message": "请求已受理"
}</code></pre>
      </div>
    </div>

    <!-- ── Status/Download ───────────────────────── -->
    <div v-if="tab==='status'" class="doc-body">
      <div class="section">
        <h3>GET /api/v1/stamp/status/{requestNo}</h3>
        <pre class="code-block"><code>{
  "requestNo": "REQ-20260604-001",
  "status": "SUCCESS",
  "message": "盖章完成",
  "created_at": "2026-06-04T10:00:00",
  "completed_at": "2026-06-04T10:00:05"
}</code></pre>
      </div>
      <div class="section">
        <h3>GET /api/v1/stamp/download/{requestNo}</h3>
        <p>返回盖章后的文件二进制流。</p>
      </div>
      <div class="section">
        <h3>回调签名</h3>
        <p>回调携带 <code>X-Stamp-Signature: sha256=...</code> 头部，用共享密钥 HMAC-SHA256 签名。</p>
        <pre class="code-block"><code>import hmac, hashlib

def verify(body: bytes, sig: str, secret: str):
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(
        f"sha256={expected}", sig
    )</code></pre>
      </div>
    </div>

    <!-- ── Keywords ──────────────────────────────── -->
    <div v-if="tab==='keywords'" class="doc-body">
      <div class="section">
        <h3>POST /api/v1/stamp/keyword-positions</h3>
        <p>搜索文件中的关键字（如「乙方盖章」），返回建议盖章坐标。</p>
        <pre class="code-block"><code>curl -X POST {base}/api/v1/stamp/keyword-positions \
  -F "file=@contract.pdf" \
  -F "keyword=乙方盖章" \
  -F "file_type=pdf"</code></pre>
      </div>
      <div class="section">
        <h3>POST /api/v1/stamp/cross-page-positions</h3>
        <p>生成骑缝章坐标（印章等分到每页边缘）。</p>
        <pre class="code-block"><code>curl -X POST {base}/api/v1/stamp/cross-page-positions \
  -F "file=@contract.pdf" \
  -F "seal_id=abc123" \
  -F "edge=right"</code></pre>
      </div>
    </div>

    <!-- ── Tester ────────────────────────────────── -->
    <div v-if="tab==='tester'" class="doc-body">
      <div class="section">
        <h4>端点</h4>
        <select v-model="teEp" class="te-select">
          <option value="submit">POST /stamp/submit</option>
          <option value="status">GET /stamp/status/{no}</option>
          <option value="health">GET /health</option>
          <option value="seals">GET /seals</option>
        </select>
      </div>
      <div v-if="teEp==='status'" class="section">
        <input v-model="teParam" class="te-input" placeholder="requestNo" />
      </div>
      <div v-if="teEp==='submit'" class="section">
        <textarea v-model="teBody" class="te-textarea" rows="14"></textarea>
        <p class="hint">修改 sealCode 和 fileUrl 后发送</p>
      </div>
      <button class="te-send" @click="sendTest" :disabled="teLoading">{{ teLoading?'发送中...':'发送' }}</button>
      <div v-if="teResp" class="te-response">
        <span class="te-status" :class="teStatus<400?'ok':'err'">HTTP {{ teStatus }}</span>
        <span class="te-time">{{ teTime }}ms</span>
        <pre class="code-block"><code>{{ teResp }}</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
const tab = ref('overview')
const base = computed(()=>window.location.origin)

const endpoints = [
  {method:'POST',path:'/api/v1/stamp/submit',desc:'异步提交盖章请求'},
  {method:'GET', path:'/api/v1/stamp/status/{no}',desc:'查询处理状态'},
  {method:'GET', path:'/api/v1/stamp/download/{no}',desc:'下载盖章文件'},
  {method:'POST',path:'/api/v1/stamp/keyword-positions',desc:'关键字定位'},
  {method:'POST',path:'/api/v1/stamp/cross-page-positions',desc:'骑缝章坐标'},
  {method:'POST',path:'/api/v1/stamp',desc:'同步盖章 (multipart)'},
  {method:'POST',path:'/api/v1/seals',desc:'上传印章'},
  {method:'GET', path:'/api/v1/seals',desc:'印章列表'},
  {method:'PATCH',path:'/api/v1/seals/{id}',desc:'修改印章'},
  {method:'DELETE',path:'/api/v1/seals/{id}',desc:'删除印章'},
  {method:'GET', path:'/api/v1/health',desc:'健康检查'},
]

const teEp=ref('submit'); const teParam=ref(''); const teBody=ref(JSON.stringify({requestNo:'TEST-'+Date.now(),fileType:'pdf',sealCode:'VP_GZ_001',fileUrl:base.value+'/api/v1/health',position:{x:420,y:680,width:120,height:120}},null,2))
const teLoading=ref(false); const teResp=ref(''); const teStatus=ref(0); const teTime=ref(0)

async function sendTest(){
  teResp.value=''; teLoading.value=true; const s=performance.now()
  try{
    let url,opts={method:'GET'}
    switch(teEp.value){
      case'submit':url='/api/v1/stamp/submit'; opts={method:'POST',headers:{'Content-Type':'application/json'},body:teBody.value}; break
      case'status':url=`/api/v1/stamp/status/${teParam.value||'NONE'}`; break
      case'health':url='/api/v1/health'; break
      case'seals':url='/api/v1/seals'; break
    }
    const r=await fetch(url,opts); teStatus.value=r.status; teTime.value=Math.round(performance.now()-s)
    const ct=r.headers.get('content-type')||''
    teResp.value=ct.includes('json')?JSON.stringify(await r.json(),null,2):(await r.text()).slice(0,2000)
  }catch(e){ teResp.value=e.message; teStatus.value=0 }
  teLoading.value=false
}
</script>

<style scoped>
.api-docs { padding:32px 40px; overflow-y:auto; height:100%; }
.docs-header { margin-bottom:20px; }
.docs-header h2 { font-size:22px; font-weight:700; }
.docs-header p { font-size:13px; color:var(--text-secondary); margin-top:4px; }

.doc-tabs { display:flex; gap:2px; background:var(--bg-page); border-radius:var(--radius-md); padding:4px; margin-bottom:24px; }
.doc-tabs button { flex:1; padding:8px 0; border:none; background:transparent; border-radius:var(--radius-sm); font-size:12px; color:var(--text-secondary); cursor:pointer; transition:all var(--fast); }
.doc-tabs button.active { background:#fff; color:var(--brand); font-weight:600; box-shadow:var(--shadow-sm); }

.doc-body { animation:fadeIn var(--normal) var(--ease); }
@keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }

.endpoint-list { background:#fff; border-radius:var(--radius-md); border:1px solid var(--border); overflow:hidden; }
.ep-row { display:flex; align-items:center; gap:12px; padding:12px 16px; border-bottom:1px solid var(--border-light); font-size:13px; }
.ep-row:last-child { border-bottom:none; }
.ep-method { padding:3px 8px; border-radius:3px; font-size:10px; font-weight:700; font-family:var(--font-mono); text-transform:uppercase; min-width:56px; text-align:center; }
.ep-method.POST { background:#ecfdf5; color:#059669; }
.ep-method.GET { background:#eff6ff; color:#2563eb; }
.ep-method.PATCH { background:#fef9c3; color:#a16207; }
.ep-method.DELETE { background:#fef2f2; color:#dc2626; }
.ep-path { font-family:var(--font-mono); font-size:12px; color:var(--text-primary); flex:1; }
.ep-desc { color:var(--text-tertiary); font-size:12px; }

.section { margin-bottom:28px; }
.section h3 { font-size:15px; font-weight:700; margin-bottom:8px; }
.section h4 { font-size:12px; color:var(--text-tertiary); margin:12px 0 6px; text-transform:uppercase; letter-spacing:.5px; }
.section p { font-size:13px; color:var(--text-secondary); line-height:1.7; }
.section code { background:var(--brand-bg); color:var(--brand); padding:1px 5px; border-radius:3px; font-size:12px; }

.code-block {
  background:#1e293b; color:#e2e8f0; padding:16px; border-radius:var(--radius-md);
  font-family:var(--font-mono); font-size:12px; line-height:1.7; overflow-x:auto; margin:8px 0;
}

.te-select,.te-input { width:100%; padding:8px 10px; border:1px solid var(--border); border-radius:var(--radius-sm); font-size:13px; }
.te-textarea { width:100%; padding:12px; border:1px solid var(--border); border-radius:var(--radius-sm); font-family:var(--font-mono); font-size:12px; background:#1e293b; color:#e2e8f0; resize:vertical; }
.hint { font-size:11px; color:var(--text-tertiary); margin-top:4px; }
.te-send { width:100%; padding:10px; border:none; background:var(--brand); color:#fff; border-radius:var(--radius-md); font-size:13px; font-weight:600; cursor:pointer; margin:12px 0; }
.te-send:disabled { opacity:.5; }
.te-response { background:#f8fafc; border:1px solid var(--border); border-radius:var(--radius-md); padding:12px; margin-top:12px; }
.te-status { font-size:11px; font-weight:700; padding:2px 8px; border-radius:3px; margin-right:8px; }
.te-status.ok { background:#ecfdf5; color:#059669; }
.te-status.err { background:#fef2f2; color:#dc2626; }
.te-time { font-size:11px; color:var(--text-tertiary); }
</style>
