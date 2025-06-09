<template>
  <div class="chat-messages-container" ref="messageContainerRef">
    <div
      v-for="msg in messages"
      :key="msg.id"
      :class="['message', msg.sender === 'user' ? 'user-message' : 'assistant-message', { 'error-message': msg.error }]"
    >
      <div class="message-content">
        <!-- Render assistant messages (not errors) with Markdown if text exists -->
        <div v-if="msg.sender === 'assistant' && !msg.error && msg.text" class="markdown-content" v-html="renderMarkdown(msg.text)"></div>
        <!-- User messages, errors, or assistant messages with no text yet (e.g. during initial stream setup before first token, or if it's an empty error message) are preformatted -->
        <pre v-else-if="msg.text || msg.sender === 'user' || (msg.sender === 'assistant' && msg.error)">{{ msg.text }}</pre>
      </div>
      <div class="message-actions">
        <button
          v-if="msg.sender === 'assistant' && !msg.error && msg.text && !msg.isStreaming"
          @click="copyMessageText(msg.text, msg.id)"
          class="copy-button"
          :title="copyStatus[msg.id] ? copyStatus[msg.id] : 'Copy text'"
        >
          {{ copyStatus[msg.id] ? (copyStatus[msg.id] === 'Copied!' ? '✅' : '❌') : '📋' }}
        </button>
      </div>
      <span v-if="msg.isStreaming" class="streaming-indicator">▍</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, defineProps } from 'vue';
import { marked } from 'marked';

const props = defineProps({
  messages: {
    type: Array,
    required: true,
    default: () => []
  }
});

const messageContainerRef = ref(null);
const copyStatus = ref({}); // Tracks copy status per message ID: { [msgId]: 'Copied!' | null }

const scrollToBottom = () => {
  if (messageContainerRef.value) {
    messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight;
  }
};

watch(
  () => props.messages,
  async () => {
    await nextTick();
    scrollToBottom();
  },
  { deep: true }
);

function renderMarkdown(text) {
  if (text === null || typeof text === 'undefined') return '';
  return marked.parse(text, { gfm: true, breaks: true });
}

async function copyMessageText(textToCopy, msgId) {
  if (!navigator.clipboard) {
    console.error('Clipboard API not available.');
    copyStatus.value[msgId] = 'Error: Clipboard API unavailable';
    setTimeout(() => { copyStatus.value[msgId] = null; }, 2000);
    return;
  }
  try {
    await navigator.clipboard.writeText(textToCopy);
    copyStatus.value[msgId] = 'Copied!';
  } catch (err) {
    console.error('Failed to copy message text:', err);
    copyStatus.value[msgId] = 'Failed!';
  }
  setTimeout(() => { copyStatus.value[msgId] = null; }, 2000); // Reset status after 2 seconds
}
</script>

<style scoped>
.chat-messages-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background-color: #ffffff;
  border: 1px solid #dee2e6;
  border-radius: 4px;
}

.message {
  display: flex; /* For aligning content and actions */
  flex-direction: column;
  padding: 10px 15px;
  border-radius: 12px;
  line-height: 1.5;
  max-width: 75%;
  word-wrap: break-word;
  position: relative;
}

.message-content {
  flex-grow: 1;
}

.message pre {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
}

.user-message {
  background-color: #007bff;
  color: white;
  align-self: flex-end;
  margin-left: auto;
  border-bottom-right-radius: 0;
}

.assistant-message {
  background-color: #e9ecef;
  color: #343a40;
  align-self: flex-start;
  margin-right: auto;
  border-bottom-left-radius: 0;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.message-actions {
  margin-top: 8px;
  text-align: right;
  height: 20px; /* Reserve space even if button not visible */
}

.copy-button {
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  padding: 2px 5px;
  font-size: 1.1em; /* Slightly larger emoji */
  opacity: 0.3;
  transition: opacity 0.2s, color 0.2s;
  position: absolute; /* Position relative to .message */
  bottom: 5px;
  right: 8px;
}

.message:hover .copy-button {
  opacity: 1;
}

.copy-button:hover {
  color: #007bff;
}


.streaming-indicator {
  display: inline-block;
  animation: blink 1s step-start 0s infinite;
  margin-left: 5px;
  font-weight: bold;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

/*
  Using :deep() to allow these styles to penetrate into the v-html rendered content.
*/
:deep(.markdown-content > *:first-child) {
  margin-top: 0;
}
:deep(.markdown-content > *:last-child) {
  margin-bottom: 0;
}

:deep(.markdown-content p) {
  margin-bottom: 0.8em;
  line-height: 1.6;
}

:deep(.markdown-content ul),
:deep(.markdown-content ol) {
  padding-left: 25px;
  margin-bottom: 0.8em;
}
:deep(.markdown-content li) {
  margin-bottom: 0.3em;
}

:deep(.markdown-content pre) {
  background-color: #2d2d2d;
  color: #f8f8f2;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 0.8em;
  font-family: 'Consolas', 'Monaco', 'Courier New', Courier, monospace;
  font-size: 0.9em;
}

/* Inline code */
:deep(.markdown-content code) {
  font-family: 'Consolas', 'Monaco', 'Courier New', Courier, monospace;
  background-color: rgba(27, 31, 35, 0.07);
  color: #c7254e;
  padding: .2em .4em;
  border-radius: 3px;
  font-size: 88%;
}

/* Code within pre should not have the inline style, but inherit from pre */
:deep(.markdown-content pre code) {
  background-color: transparent;
  color: inherit;
  padding: 0;
  font-size: inherit;
  border-radius: 0;
}


:deep(.markdown-content blockquote) {
  border-left: 4px solid #adb5bd;
  padding-left: 15px;
  margin-left: 0;
  margin-bottom: 0.8em;
  color: #495057;
  font-style: italic;
}

:deep(.markdown-content h1),
:deep(.markdown-content h2),
:deep(.markdown-content h3),
:deep(.markdown-content h4),
:deep(.markdown-content h5),
:deep(.markdown-content h6) {
  margin-top: 1.2em;
  margin-bottom: 0.6em;
  font-weight: 600;
  color: #343a40;
  line-height: 1.25;
}
:deep(.markdown-content h1) { font-size: 1.8em; }
:deep(.markdown-content h2) { font-size: 1.5em; }
:deep(.markdown-content h3) { font-size: 1.25em; }

:deep(.markdown-content table) {
  width: auto;
  border-collapse: collapse;
  margin-bottom: 1em;
  font-size: 0.9em;
  border: 1px solid #dee2e6;
}
:deep(.markdown-content th),
:deep(.markdown-content td) {
  border: 1px solid #dee2e6;
  padding: 8px 12px;
  text-align: left;
}
:deep(.markdown-content th) {
  background-color: #f8f9fa;
  font-weight: 600;
}
:deep(.markdown-content tr:nth-child(even)) {
  background-color: #fdfdfd;
}
</style>
