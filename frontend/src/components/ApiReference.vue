<template>
  <div class="api-reference">
    <h3>📡 外部调用 API</h3>

    <!-- Tabs -->
    <div class="tabs">
      <button :class="{ active: tab === 'format' }" @click="tab = 'format'">请求格式</button>
      <button :class="{ active: tab === 'tester' }" @click="tab = 'tester'">🧪 测试工具</button>
      <button :class="{ active: tab === 'curl' }" @click="tab = 'curl'">curl 示例</button>
      <button :class="{ active: tab === 'callback' }" @click="tab = 'callback'">回调说明</button>
    </div>

    <!-- ── JSON Format ──────────────────────────────── -->
    <div v-if="tab === 'format'" class="tab-content">
      <div class="endpoint-tag">POST /api/v1/stamp/submit</div>
      <pre class="code"><code>{{ jsonSample }}</code></pre>
    </div>

    <!-- ── 🧪 Interactive Tester ────────────────────── -->
    <div v-if="tab === 'tester'" class="tab-content">
      <div class="section">
        <h4>端点</h4>
        <select v-model="testerEndpoint" class="ep-select">
          <option value="submit">POST /api/v1/stamp/submit — 提交盖章</option>
          <option value="status">GET  /api/v1/stamp/status/{no} — 查询状态</option>
          <option value="download">GET  /api/v1/stamp/download/{no} — 下载文件</option>
          <option value="seals">GET  /api/v1/seals — 印章列表</option>
          <option value="health">GET  /api/v1/health — 健康检查</option>
        </select>
      </div>

      <!-- Path param (for status/download) -->
      <div class="section" v-if="['status', 'download'].includes(testerEndpoint)">
        <h4>requestNo</h4>
        <input v-model="testerParam" class="param-input" placeholder="REQ-20260604-001" />
      </div>

      <!-- JSON body (for submit) -->
      <div v-if="testerEndpoint === 'submit'" class="section">
        <h4>请求体 (JSON)</h4>
        <textarea
          v-model="testerBody"
          class="body-editor"
          rows="14"
          spellcheck="false"
        ></textarea>
        <div class="btn-row">
          <button class="btn-reset" @click="resetTesterBody">重置默认</button>
        </div>
      </div>

      <!-- Send button -->
      <button class="btn-send" @click="sendTester" :disabled="testerLoading">
        {{ testerLoading ? '发送中...' : '🚀 发送请求' }}
      </button>

      <!-- Response -->
      <div v-if="testerResponse" class="section response-block">
        <h4>
          响应
          <span :class="['status-badge', testerStatus < 400 ? 'ok' : 'err']">
            HTTP {{ testerStatus }}
          </span>
          <span class="resp-time">{{ testerTime }}ms</span>
        </h4>
        <pre class="code"><code>{{ testerResponse }}</code></pre>
        <button class="btn-copy" @click="copyResponse">📋 复制</button>
      </div>

      <!-- Error -->
      <div v-if="testerError" class="section response-block error-block">
        <h4>❌ 错误</h4>
        <pre class="code error-code"><code>{{ testerError }}</code></pre>
      </div>
    </div>

    <!-- ── curl Example ─────────────────────────────── -->
    <div v-if="tab === 'curl'" class="tab-content">
      <div class="section">
        <h4>提交盖章任务</h4>
        <pre class="code"><code>curl -X POST {{ baseUrl }}/api/v1/stamp/submit \
  -H "Content-Type: application/json" \
  -d '{
    "requestNo": "REQ-20260604-001",
    "sealCode": "VP_GZ_001",
    "fileUrl": "https://example.com/contract.pdf",
    "position": {"x":420,"y":680,"width":120,"height":120},
    "callbackUrl": "https://your-system/callback"
  }'</code></pre>
      </div>
      <div class="section">
        <h4>查询任务状态</h4>
        <pre class="code"><code>curl {{ baseUrl }}/api/v1/stamp/status/REQ-20260604-001</code></pre>
      </div>
      <div class="section">
        <h4>下载盖章文件</h4>
        <pre class="code"><code>curl -OJ {{ baseUrl }}/api/v1/stamp/download/REQ-20260604-001</code></pre>
      </div>
    </div>

    <!-- ── Callback ─────────────────────────────────── -->
    <div v-if="tab === 'callback'" class="tab-content">
      <div class="section">
        <h4>回调请求体</h4>
        <pre class="code"><code>{
  "requestNo": "REQ-20260604-001",
  "status": "SUCCESS",
  "message": "",
  "downloadUrl": "/api/v1/stamp/download/REQ-..."
}</code></pre>
      </div>
      <div class="section">
        <h4>HMAC 签名验证</h4>
        <p class="hint">
          回调携带 <code>X-Stamp-Signature: sha256=...</code> 头部
        </p>
        <pre class="code"><code>import hmac, hashlib

def verify(body: bytes, sig: str, secret: str):
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(
        f"sha256={expected}", sig
    )</code></pre>
      </div>
    </div>

    <!-- Status -->
    <div class="status-bar">
      <span :class="['dot', apiOk ? 'green' : 'red']"></span>
      API {{ apiOk ? '可达' : '不可达' }}
      <button class="btn-test" @click="testApi">测试</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'

const tab = ref('tester')
const apiOk = ref(false)
const baseUrl = computed(() => window.location.origin)

// ── Tester state ────────────────────────────────────
const testerEndpoint = ref('submit')
const testerParam    = ref('')
const testerBody     = ref('')
const testerLoading  = ref(false)
const testerResponse = ref('')
const testerStatus   = ref(0)
const testerTime     = ref(0)
const testerError    = ref('')

const defaultTesterBody = computed(() => {
  const ts = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14)
  return JSON.stringify({
    requestNo: `TEST-${ts}`,
    businessId: "BIZ-TEST",
    systemCode: "TEST",
    systemName: "测试系统",
    fileType: "pdf",
    sealCode: "VP_GZ_001",
    fileUrl: `${baseUrl.value}/api/v1/health`,  // placeholder, replace with real PDF URL
    callbackUrl: "",
    position: { x: 420, y: 680, width: 120, height: 120, page: 1, rotation: 0 },
  }, null, 2)
})

function resetTesterBody() { testerBody.value = defaultTesterBody.value }

onMounted(() => {
  resetTesterBody()
  testApi()
})

async function sendTester() {
  testerResponse.value = ''
  testerError.value    = ''
  testerLoading.value  = true
  const start = performance.now()

  try {
    let url, method, body

    switch (testerEndpoint.value) {
      case 'submit':
        url = '/api/v1/stamp/submit'
        method = 'POST'
        body = testerBody.value
        break
      case 'status':
        url = `/api/v1/stamp/status/${testerParam.value || 'NONE'}`
        method = 'GET'
        break
      case 'download':
        url = `/api/v1/stamp/download/${testerParam.value || 'NONE'}`
        method = 'GET'
        break
      case 'seals':
        url = '/api/v1/seals'
        method = 'GET'
        break
      case 'health':
        url = '/api/v1/health'
        method = 'GET'
        break
      default:
        throw new Error('Unknown endpoint')
    }

    const opts = { method }
    if (body) {
      opts.headers = { 'Content-Type': 'application/json' }
      opts.body = body
    }

    const res = await fetch(url, opts)
    testerStatus.value = res.status
    testerTime.value   = Math.round(performance.now() - start)

    const ct = res.headers.get('content-type') || ''
    if (ct.includes('application/json')) {
      const json = await res.json()
      testerResponse.value = JSON.stringify(json, null, 2)
    } else {
      const text = await res.text()
      testerResponse.value = text.slice(0, 2000)
    }
  } catch (e) {
    testerError.value = e.message
  } finally {
    testerLoading.value = false
  }
}

function copyResponse() {
  navigator.clipboard.writeText(testerResponse.value)
  ElMessage.success('已复制')
}

async function testApi() {
  try {
    const res = await fetch('/api/v1/health')
    apiOk.value = res.ok
  } catch { apiOk.value = false }
}

// ── Static ─────────────────────────────────────────
const jsonSample = JSON.stringify({
  requestNo: "REQ-20260604-001",
  businessId: "BIZ-123",
  systemCode: "VP",
  systemName: "可视化平台",
  fileType: "pdf",
  sealCode: "VP_GZ_001",
  fileUrl: "https://your-system/files/contract.pdf",
  callbackUrl: "https://your-system/api/callback",
  position: { x: 420, y: 680, width: 120, height: 120, page: 1, rotation: 0 },
}, null, 2)
</script>

<style scoped>
.api-reference {
  padding: 16px;
  font-size: 13px;
  color: #303133;
}
.api-reference h3 {
  font-size: 15px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8eaed;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 3px;
  margin-bottom: 12px;
  background: #e8eaed;
  border-radius: 6px;
  padding: 3px;
  flex-wrap: wrap;
}
.tabs button {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 6px 2px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #606266;
  transition: all .15s;
  white-space: nowrap;
}
.tabs button.active {
  background: #fff;
  color: #409eff;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}

/* Content */
.tab-content { animation: fadeIn .2s ease; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.section { margin-bottom: 14px; }
.section h4 {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
  font-weight: 500;
}

.endpoint-tag {
  display: inline-block;
  background: #ecf5ff;
  color: #409eff;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 10px;
}

/* ── Tester controls ─────────────────────────────── */
.ep-select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 12px;
  background: #fff;
  color: #303133;
}
.param-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
}
.body-editor {
  width: 100%;
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  background: #1e1e2e;
  color: #cdd6f4;
  resize: vertical;
  line-height: 1.5;
}
.btn-row { margin-top: 6px; display: flex; gap: 8px; }
.btn-reset {
  border: 1px solid #dcdfe6;
  background: #fff;
  padding: 3px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #606266;
}
.btn-reset:hover { border-color: #409eff; color: #409eff; }

.btn-send {
  width: 100%;
  padding: 8px;
  border: none;
  border-radius: 6px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity .15s;
}
.btn-send:hover:not(:disabled) { opacity: .9; }
.btn-send:disabled { opacity: .5; cursor: not-allowed; }

/* ── Response ─────────────────────────────────────── */
.response-block {
  background: #fafbfc;
  border: 1px solid #e8eaed;
  border-radius: 6px;
  padding: 10px;
}
.response-block h4 {
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-badge {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 3px;
  font-weight: 600;
}
.status-badge.ok  { background: #e1f3d8; color: #67c23a; }
.status-badge.err { background: #fde2e2; color: #f56c6c; }
.resp-time { color: #c0c4cc; font-size: 11px; }

.error-block { border-color: #fde2e2; background: #fef0f0; }
.error-code { background: #2d1111 !important; color: #fca5a5 !important; }

.btn-copy {
  margin-top: 8px;
  border: 1px solid #dcdfe6;
  background: #fff;
  padding: 3px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}

/* Code */
.code {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 12px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre;
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  max-height: 300px;
  overflow-y: auto;
}
.hint {
  color: #909399;
  font-size: 11px;
  line-height: 1.6;
  margin-bottom: 8px;
}
.hint code {
  background: #ecf5ff;
  color: #409eff;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11px;
}

/* Status bar */
.status-bar {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e8eaed;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
}
.dot { width: 7px; height: 7px; border-radius: 50%; }
.dot.green { background: #67c23a; }
.dot.red   { background: #f56c6c; }
.btn-test {
  margin-left: auto;
  border: 1px solid #dcdfe6;
  background: #fff;
  padding: 2px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #606266;
  transition: all .15s;
}
.btn-test:hover { border-color: #409eff; color: #409eff; }
</style>
