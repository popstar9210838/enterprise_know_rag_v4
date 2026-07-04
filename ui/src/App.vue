<template>
  <div class="app">
    <header class="header">
      <h1>企业知识库 RAG</h1>
      <button class="btn-reset" @click="resetSession">新对话</button>
    </header>
    <div class="main">
      <ManagePanel />
      <ChatPanel ref="chatPanel" />
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import ChatPanel from "./components/ChatPanel.vue";
import ManagePanel from "./components/ManagePanel.vue";

const chatPanel = ref(null);

function resetSession() {
  chatPanel.value?.clearMessages();
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.app {
  max-width: 1100px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #e5e5e5;
  flex-shrink: 0;
}
.header h1 {
  font-size: 18px;
  font-weight: 600;
}
.btn-reset {
  padding: 6px 16px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.btn-reset:hover {
  background: #f5f5f5;
}
.main {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
