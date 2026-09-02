<template>
  <div class="app">
    <header class="header">
      <h1>企业知识库 RAG</h1>
      <button class="btn-reset" @click="resetSession">新对话</button>
    </header>
    <div class="main">
      <ManagePanel v-show="!isMobile || activeTab === 'manage'" />
      <ChatPanel
        ref="chatPanel"
        v-show="!isMobile || activeTab === 'chat'"
        :active="!isMobile || activeTab === 'chat'"
      />
    </div>
    <nav class="tab-bar">
      <button
        class="tab"
        role="tab"
        :class="{ active: activeTab === 'chat' }"
        :aria-selected="activeTab === 'chat'"
        @click="activeTab = 'chat'"
      >问答</button>
      <button
        class="tab"
        role="tab"
        :class="{ active: activeTab === 'manage' }"
        :aria-selected="activeTab === 'manage'"
        @click="activeTab = 'manage'"
      >管理</button>
    </nav>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import ChatPanel from "./components/ChatPanel.vue";
import ManagePanel from "./components/ManagePanel.vue";

const chatPanel = ref(null);
const isMobile = ref(false);
const activeTab = ref("chat"); // "chat" | "manage"
let mediaQuery = null;

function onMediaChange(e) {
  isMobile.value = e.matches;
}

onMounted(() => {
  mediaQuery = window.matchMedia("(max-width: 767px)");
  onMediaChange(mediaQuery);
  mediaQuery.addEventListener("change", onMediaChange);
});

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener("change", onMediaChange);
});

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
  height: 100dvh; /* iOS Safari 视口兜底 */
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
.tab-bar {
  display: none; /* 仅移动端显示 */
}
@media (max-width: 767px) {
  .header {
    padding: 8px 16px;
    padding-top: calc(8px + env(safe-area-inset-top));
  }
  .header h1 {
    font-size: 16px;
  }
  .btn-reset {
    min-height: 44px;
    padding: 8px 16px;
  }
  .main {
    flex-direction: column;
  }
  .tab-bar {
    display: flex;
    flex-shrink: 0;
    border-top: 1px solid #e5e5e5;
    background: #fff;
    padding-bottom: env(safe-area-inset-bottom);
  }
  .tab {
    flex: 1;
    min-height: 52px; /* 44px 触控目标 + 安全区余量 */
    border: none;
    background: none;
    font-size: 14px;
    color: #666;
    cursor: pointer;
  }
  .tab:active {
    background: #f5f5f5;
  }
  .tab.active {
    color: #2563eb;
    font-weight: 600;
  }
}
</style>
