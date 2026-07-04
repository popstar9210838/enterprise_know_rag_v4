<template>
  <div class="chat-panel">
    <div class="messages" ref="msgContainer">
      <div v-if="messages.length === 0" class="empty">
        <p>输入问题开始对话</p>
        <div v-if="sampleQuestions.length" class="sample-questions">
          <span class="sample-label">你可以这样问：</span>
          <button
            v-for="q in sampleQuestions"
            :key="q"
            class="sample-chip"
            @click="sendSample(q)"
          >{{ q }}</button>
        </div>
      </div>
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['message', msg.role]"
      >
        <div class="role-label">{{ msg.role === "user" ? "你" : "AI" }}</div>
        <div class="content" v-text="msg.text"></div>
        <SourceCard v-if="msg.sources?.length" :sources="msg.sources" />
        <span v-if="msg.streaming" class="cursor">|</span>
      </div>
    </div>

    <div class="input-area">
      <input
        ref="inputRef"
        v-model="question"
        @keydown.enter="send"
        placeholder="输入问题，按 Enter 发送..."
        :disabled="loading"
      />
      <button @click="send" :disabled="loading || !question.trim()">
        {{ loading ? "..." : "发送" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";
import SourceCard from "./SourceCard.vue";
import { queryStream, getSampleQuestions } from "../api/index.js";

const messages = ref([]);
const question = ref("");
const loading = ref(false);
const msgContainer = ref(null);
const inputRef = ref(null);
const sampleQuestions = ref([]);

onMounted(async () => {
  try {
    const data = await getSampleQuestions();
    sampleQuestions.value = data.questions || [];
  } catch {
    // 获取失败静默，不影响主流程
  }
});

function sendSample(q) {
  question.value = q;
  send();
}

async function send() {
  const q = question.value.trim();
  if (!q || loading.value) return;

  // 1. 插入用户消息
  messages.value.push({ role: "user", text: q });

  // 2. 预备 AI 空白消息
  const aiMsg = ref({ role: "ai", text: "", sources: null, streaming: true });
  messages.value.push(aiMsg.value);

  question.value = "";
  loading.value = true;

  await nextTick();
  scrollBottom();

  // 💡 【核心修改 2】删掉所有冗余的 fetch、buffer、split 拆分逻辑，直接用 API
  queryStream(q, {
    // 收到来源节点回调
    onSources: (sources) => {
      aiMsg.value.sources = sources;
    },
    // 收到逐字 token 回调
    onToken: (token) => {
      aiMsg.value.text += token;
      // 利用 requestAnimationFrame 配合 Vue 异步渲染，体验最丝滑
      requestAnimationFrame(() => {
        scrollBottom();
      });
    },
    // 生成完毕回调
    onDone: () => {
      aiMsg.value.streaming = false;
      loading.value = false;
      nextTick(() => {
        inputRef.value?.focus();
      });
    },
    // 异常捕获回调
    onError: (err) => {
      aiMsg.value.text = `请求失败: ${err.message}`;
      aiMsg.value.streaming = false;
      loading.value = false;
    }
  });
}

function scrollBottom() {
  const el = msgContainer.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
}

function clearMessages() {
  messages.value = [];
}

defineExpose({ clearMessages });
</script>

<style scoped>
/* 保持你原本的样式不变 */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.empty {
  text-align: center;
  color: #999;
  margin-top: 120px;
  font-size: 15px;
}
.sample-questions {
  margin-top: 24px;
}
.sample-label {
  display: block;
  margin-bottom: 12px;
  color: #888;
  font-size: 13px;
}
.sample-chip {
  display: inline-block;
  margin: 4px 6px;
  padding: 8px 16px;
  border: 1px solid #d0d0d0;
  border-radius: 20px;
  background: #fff;
  color: #333;
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}
.sample-chip:hover {
  border-color: #2563eb;
  color: #2563eb;
}
.message {
  margin-bottom: 20px;
  animation: fadeIn 0.2s;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.role-label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}
.message.user .role-label {
  color: #2563eb;
}
.content {
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.cursor {
  display: inline;
  animation: blink 0.8s infinite;
  color: #2563eb;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.input-area {
  display: flex;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid #e5e5e5;
  flex-shrink: 0;
}
.input-area input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}
.input-area input:focus {
  border-color: #2563eb;
}
.input-area button {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.input-area button:disabled {
  background: #a0c4ff;
  cursor: not-allowed;
}
</style>