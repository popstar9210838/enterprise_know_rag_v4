<template>
  <div class="manage-panel">
    <h2>知识库管理</h2>

    <div class="status">
      文档块数：<strong>{{ chunks }}</strong>
      <button class="btn-refresh" @click="refresh" :disabled="refreshing">刷新</button>
    </div>

    <div class="upload-area">
      <input
        ref="fileInput"
        type="file"
        multiple
        @change="onFilesSelected"
        :accept="acceptTypes"
        hidden
      />
      <button class="btn btn-upload" @click="fileInput?.click()" :disabled="busy">
        添加文档
      </button>
      <span v-if="selectedFiles.length" class="file-count">
        已选 {{ selectedFiles.length }} 个文件
      </span>
      <ul v-if="selectedFiles.length" class="file-list">
        <li v-for="(f, i) in selectedFiles" :key="i">{{ f.name }}</li>
      </ul>
      <button
        v-if="selectedFiles.length"
        class="btn btn-upload"
        @click="doUpload"
        :disabled="busy || uploading"
      >
        {{ uploading ? "上传中..." : "上传" }}
      </button>
    </div>

    <div class="actions">
      <button class="btn btn-sync" @click="doBuild" :disabled="busy">同步索引</button>
      <button class="btn btn-delete" @click="doDelete" :disabled="busy">删除索引</button>
    </div>

    <div v-if="message" :class="['msg', message.type]">{{ message.text }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { getStatus, build, deleteIndex, uploadFiles } from "../api/index.js";

const acceptTypes = import.meta.env.VITE_SUPPORTED_EXTENSIONS;

const fileInput = ref(null);
const chunks = ref(0);
const refreshing = ref(false);
const busy = ref(false);
const uploading = ref(false);
const message = ref(null);
const selectedFiles = ref([]);

function onFilesSelected(e) {
  selectedFiles.value = Array.from(e.target.files);
}

function showMsg(text, type = "info") {
  message.value = { text, type };
  setTimeout(() => { message.value = null; }, 4000);
}

async function refresh() {
  refreshing.value = true;
  try {
    const status = await getStatus();
    chunks.value = status.chunks;
  } catch (e) {
    showMsg(`获取状态失败: ${e.message}`, "error");
  } finally {
    refreshing.value = false;
  }
}

function wrap(label, fn) {
  return async () => {
    if (busy.value) return;
    busy.value = true;
    try {
      const res = await fn();
      chunks.value = res.chunks;
      showMsg(`${label}完成，共 ${res.chunks} 个文档块`, "info");
    } catch (e) {
      showMsg(`${label}失败: ${e.message}`, "error");
    } finally {
      busy.value = false;
    }
  };
}

const doBuild = wrap("同步索引", build);

async function doDelete() {
  if (busy.value) return;
  if (!confirm("确定要删除整个索引吗？此操作不可逆。")) return;
  busy.value = true;
  try {
    await deleteIndex();
    chunks.value = 0;
    showMsg("索引已删除", "info");
  } catch (e) {
    showMsg(`删除失败: ${e.message}`, "error");
  } finally {
    busy.value = false;
  }
}

async function doUpload() {
  if (busy.value || !selectedFiles.value.length) return;
  uploading.value = true;
  try {
    const res = await uploadFiles(selectedFiles.value);
    showMsg(`已上传 ${res.count} 个文件，请点击"同步索引"生效`, "info");
    selectedFiles.value = [];
    fileInput.value.value = "";
  } catch (e) {
    showMsg(`上传失败: ${e.message}`, "error");
  } finally {
    uploading.value = false;
  }
}

onMounted(refresh);
</script>

<style scoped>
.manage-panel {
  padding: 20px;
  border-right: 1px solid #e5e5e5;
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
h2 {
  font-size: 16px;
  font-weight: 600;
}
.status {
  font-size: 13px;
  color: #555;
}
.status strong {
  color: #2563eb;
  font-size: 16px;
}
.btn-refresh {
  margin-left: 8px;
  padding: 2px 10px;
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  background: #fff;
  font-size: 12px;
  cursor: pointer;
}
.upload-area {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.file-count {
  font-size: 12px;
  color: #666;
}
.file-list {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
  color: #555;
  max-height: 100px;
  overflow-y: auto;
}
.file-list li {
  word-break: break-all;
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.btn {
  padding: 8px 14px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: #fff;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-upload { background: #7c3aed; }
.btn-sync { background: #2563eb; }
.btn-delete { background: #dc2626; }
.msg {
  font-size: 12px;
  padding: 8px;
  border-radius: 6px;
  line-height: 1.5;
}
.msg.info { background: #dbeafe; color: #1e40af; }
.msg.error { background: #fee2e2; color: #991b1b; }
</style>
