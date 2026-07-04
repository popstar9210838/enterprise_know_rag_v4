<template>
  <div class="sources">
    <details>
      <summary>📎 来源 ({{ sources.length }})</summary>
      <div v-for="(s, i) in sources" :key="i" class="source-item">
        <a
          class="source-file"
          :href="`${previewBase}?file=${encodeURIComponent(s.file)}`"
          target="_blank"
        >{{ s.file }}</a>
        <span class="source-score">score: {{ s.score }}</span>
        <p class="source-preview">{{ s.preview }}</p>
      </div>
    </details>
  </div>
</template>

<script setup>
const previewBase = import.meta.env.VITE_API_BASE + "/preview";

defineProps({
  sources: { type: Array, default: () => [] },
});
</script>

<style scoped>
.sources {
  margin-top: 8px;
}
summary {
  font-size: 12px;
  color: #888;
  cursor: pointer;
}
.source-item {
  margin-top: 6px;
  padding: 8px;
  border-radius: 6px;
  background: #f8f8f8;
  font-size: 12px;
}
.source-file {
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;
}
.source-file:hover {
  text-decoration: underline;
}
.source-score {
  margin-left: 8px;
  color: #999;
}
.source-preview {
  margin-top: 4px;
  color: #666;
  line-height: 1.5;
}
</style>