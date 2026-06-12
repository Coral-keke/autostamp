<template>
  <div class="file-uploader">
    <el-upload
      class="upload-drop"
      drag
      :auto-upload="false"
      :on-change="onFileChange"
      :accept="'.pdf,.dwg,.png,.jpg,.jpeg,.docx,.xlsx'"
      :limit="1"
    >
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <div class="upload-text">
        <p><strong>拖拽或点击上传文件</strong></p>
        <p class="hint">支持 PDF / DWG / PNG / JPG / Word / Excel，最大 100MB</p>
      </div>
    </el-upload>
  </div>
</template>

<script setup>
import { UploadFilled } from '@element-plus/icons-vue'

const emit = defineEmits(['uploaded'])

function onFileChange(file) {
  emit('uploaded', file.raw)
}
</script>

<style scoped>
.file-uploader {
  width: 500px;
}
.upload-drop {
  width: 100%;
}
.upload-icon {
  font-size: 48px;
  color: #409eff;
}
.upload-text {
  margin-top: 12px;
}
.hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>
