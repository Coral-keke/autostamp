<template>
  <div class="seal-library">
    <h3>📦 印章库</h3>

    <!-- Upload -->
    <div class="upload-area">
      <input
        ref="fileInput"
        type="file"
        accept="image/png,image/jpeg,image/svg+xml"
        style="display: none"
        @change="onFileSelected"
      />
      <el-button type="primary" size="small" @click="$refs.fileInput.click()">
        + 上传印章
      </el-button>
      <el-form v-if="uploadForm.name" class="upload-form" label-width="60px" size="small">
        <el-form-item label="名称">
          <el-input v-model="uploadForm.name" placeholder="印章名称" />
        </el-form-item>
        <el-form-item label="宽(mm)">
          <el-input-number v-model="uploadForm.width" :min="5" :max="200" />
        </el-form-item>
        <el-form-item label="高(mm)">
          <el-input-number v-model="uploadForm.height" :min="5" :max="200" />
        </el-form-item>
        <el-button type="success" size="small" @click="doUpload">确认上传</el-button>
        <el-button size="small" @click="resetUpload">取消</el-button>
      </el-form>
    </div>

    <!-- Seal Grid -->
    <div class="seal-grid" v-if="seals.length">
      <div
        v-for="seal in seals"
        :key="seal.id"
        class="seal-item"
        :class="{ selected: selectedId === seal.id }"
        draggable="true"
        @dragstart="onDragStart(seal, $event)"
        @click="$emit('select', seal)"
      >
        <img :src="getSealImageUrl(seal.id)" :alt="seal.name" />
        <span class="seal-name">{{ seal.name }}</span>
        <span class="seal-code">{{ seal.seal_code }}</span>
        <div class="seal-actions">
          <el-button class="action-btn" size="small" circle @click.stop="openEdit(seal)">
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-button class="action-btn delete-btn" type="danger" size="small" circle @click.stop="$emit('delete', seal.id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
    <el-empty v-else description="暂无印章，请上传" />

    <!-- Edit Dialog -->
    <el-dialog v-model="editVisible" title="修改印章" width="400px">
      <el-form :model="editForm" label-width="80px" size="small">
        <el-form-item label="编码">
          <el-input v-model="editForm.seal_code" placeholder="sealCode" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="editForm.name" placeholder="印章名称" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="editForm.seal_type">
            <el-option label="公章" value="OFFICIAL" />
            <el-option label="合同章" value="CONTRACT" />
            <el-option label="财务章" value="FINANCE" />
            <el-option label="签名章" value="SIGNATURE" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="doEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, reactive } from 'vue'
import { Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getSealImageUrl, updateSeal } from '../api/index.js'

const props = defineProps({
  seals: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' },
})

const emit = defineEmits(['upload', 'delete', 'select'])

const fileInput = ref(null)
const uploadForm = ref({ name: '', width: 40, height: 40, file: null })

function onFileSelected(e) {
  const file = e.target.files[0]
  if (!file) return
  uploadForm.value.file = file
  uploadForm.value.name = file.name.replace(/\.[^.]+$/, '')
}

function doUpload() {
  if (!uploadForm.value.file) return
  const fd = new FormData()
  fd.append('file', uploadForm.value.file)
  fd.append('name', uploadForm.value.name)
  fd.append('default_width_mm', uploadForm.value.width)
  fd.append('default_height_mm', uploadForm.value.height)
  emit('upload', fd)
  resetUpload()
}

function resetUpload() {
  uploadForm.value = { name: '', width: 40, height: 40, file: null }
  if (fileInput.value) fileInput.value.value = ''
}

function onDragStart(seal, event) {
  event.dataTransfer.setData('application/seal-id', seal.id)
  event.dataTransfer.setData('application/seal-width', seal.default_width_mm)
  event.dataTransfer.setData('application/seal-height', seal.default_height_mm)
  event.dataTransfer.effectAllowed = 'copy'
}

// ── Edit seal ────────────────────────────────────────────

const editVisible = ref(false)
const editForm = reactive({
  id: '', seal_code: '', name: '', seal_type: 'OFFICIAL', description: '',
})

function openEdit(seal) {
  editForm.id = seal.id
  editForm.seal_code = seal.seal_code
  editForm.name = seal.name
  editForm.seal_type = seal.seal_type
  editForm.description = seal.description
  editVisible.value = true
}

async function doEdit() {
  const fd = new FormData()
  fd.append('seal_code', editForm.seal_code)
  fd.append('name', editForm.name)
  fd.append('seal_type', editForm.seal_type)
  fd.append('description', editForm.description)
  try {
    await updateSeal(editForm.id, fd)
    ElMessage.success('印章已更新')
    editVisible.value = false
    emit('refresh')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  }
}
</script>

<style scoped>
.seal-library { padding: 16px; }
.seal-library h3 { margin-bottom: 12px; font-size: 16px; }

.upload-area { margin-bottom: 16px; }
.upload-form { margin-top: 12px; padding: 12px; background: #fff; border-radius: 8px; }

.seal-grid { display: flex; flex-wrap: wrap; gap: 12px; }
.seal-item {
  width: 110px;
  padding: 8px;
  background: #fff;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  text-align: center;
  cursor: grab;
  position: relative;
  transition: border-color .2s;
}
.seal-item:hover { border-color: #409eff; }
.seal-item.selected { border-color: #409eff; background: #ecf5ff; }
.seal-item img {
  width: 80px;
  height: 80px;
  object-fit: contain;
  pointer-events: none;
}
.seal-name {
  display: block;
  font-size: 11px;
  color: #606266;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.seal-code {
  display: block;
  font-size: 9px;
  color: #999;
  font-family: monospace;
  margin-top: 2px;
}
.seal-actions {
  display: flex;
  justify-content: center;
  gap: 4px;
  margin-top: 6px;
}
.action-btn {
  width: 22px !important;
  height: 22px !important;
  font-size: 10px !important;
  padding: 0 !important;
}
</style>
