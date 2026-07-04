/**
 * API 层 —— 对接 server.py 的全部端点。
 */
const BASE = import.meta.env.VITE_API_BASE;

/** 获取示例问题列表 */
export async function getSampleQuestions() {
  const res = await fetch(`${BASE}/sample-questions`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json(); // {questions: [...]}
}

/** 获取服务状态（chunk 数） */
export async function getStatus() {
  const res = await fetch(`${BASE}/chunks`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json(); // {chunks: N}
}

/** 非流式查询 */
export async function query(question) {
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json(); // {answer: str, sources: [...]}
}

/** 流式查询（SSE） */
export function queryStream(question, { onSources, onToken, onDone, onError }) {
  fetch(`${BASE}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // 封装单行解析逻辑，提高复用性
      const parseLine = (line) => {
        if (!line.startsWith("data: ")) return false;
        const payload = line.slice(6).trim();

        if (payload === "[DONE]") {
          return true; // 标记收到明确结束符
        }

        try {
          const msg = JSON.parse(payload);
          if (msg.type === "sources") {
            onSources?.(msg.sources);
          } else if (msg.type === "token") {
            onToken?.(msg.token);
          }
        } catch {
          // 降级处理：兼容纯文本内容
          onToken?.(payload);
        }
        return false;
      };

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (value) {
            // 用 stream: true 确保多字节汉字被截断时不会解码出乱码
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              const isDone = parseLine(line);
              if (isDone) {
                onDone?.();
                return; // 显式收到 [DONE]，直接退出
              }
            }
          }

          if (done) {
            // 兜底处理：解析最后可能残留在 buffer 中没有换行符的数据
            if (buffer.trim()) {
              parseLine(buffer);
            }
            break;
          }
        }

        // 流正常结束的兜底触发
        onDone?.();

      } finally {
        // 无论成功还是异常，都必须释放 reader 锁，防止内存泄漏
        reader.releaseLock();
      }
    })
    .catch((e) => {
      onError?.(e);
    });
}

// ── 知识库管理 ──

export async function build() {
  const res = await fetch(`${BASE}/build`, { method: "POST" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json(); // {ok: true, chunks: N}
}

export async function rebuild() {
  const res = await fetch(`${BASE}/rebuild`, { method: "POST" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function ingest() {
  const res = await fetch(`${BASE}/ingest`, { method: "POST" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function deleteIndex() {
  const res = await fetch(`${BASE}/index`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

/** 上传文件到 data/ 目录 */
export async function uploadFiles(files) {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json(); // {ok: true, saved: [...], count: N}
}