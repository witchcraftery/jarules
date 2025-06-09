<template>
  <div class="chat-input-area">
    <textarea
      ref="textareaRef"
      v-model="inputText"
      @keydown="handleKeydown"
      :disabled="isStreaming"
      placeholder="Type your message (Shift+Enter for new line)..."
      rows="1"
    ></textarea>
    <button
      @click="submitPrompt"
      :disabled="isStreaming || !inputText.trim()"
    >
      {{ isStreaming ? 'Generating...' : 'Send' }}
    </button>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, nextTick } from 'vue';

const props = defineProps({
  isStreaming: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['send-prompt']);

const inputText = ref('');
const textareaRef = ref(null); // For auto-resize

const adjustTextareaHeight = () => {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'; // Reset height to shrink if needed
    // Set a slight delay or use nextTick if scrollHeight isn't updated immediately
    nextTick(() => {
      if (textareaRef.value) { // Check again as it's in nextTick
         // Max height check before setting new height
        const maxHeight = parseInt(getComputedStyle(textareaRef.value).maxHeight, 10) || 150; // 150 from CSS
        const scrollHeight = textareaRef.value.scrollHeight;
        if (scrollHeight > maxHeight) {
            textareaRef.value.style.height = maxHeight + 'px';
            textareaRef.value.style.overflowY = 'auto'; // Ensure scrollbar appears if content exceeds max-height
        } else {
            textareaRef.value.style.height = scrollHeight + 'px';
            textareaRef.value.style.overflowY = 'hidden'; // Hide scrollbar if content is less than max-height
        }
      }
    });
  }
};

const submitPrompt = () => {
  const trimmedText = inputText.value.trim();
  if (trimmedText) {
    emit('send-prompt', trimmedText);
    inputText.value = ''; // Clear input
    // After sending, reset textarea height as content is cleared
    nextTick(() => adjustTextareaHeight());
  }
};

const handleKeydown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault(); // Prevent default Enter behavior (new line)
    submitPrompt();
  }
  // Adjust height on keydown as well, especially for paste or multiline changes
  // but primarily on input event for typing.
  // For simplicity, we'll call it on input via v-on:input or rely on keydown.
  // Let's add @input to the textarea for more responsive height adjustment.
};

// Watch inputText for changes to adjust height (alternative to @input)
watch(inputText, () => {
  adjustTextareaHeight();
});

</script>

<style scoped>
.chat-input-area {
  display: flex;
  align-items: flex-start; /* Align items to the top for when textarea grows */
  padding: 12px;
  border-top: 1px solid #ced4da; /* Separator from messages */
  background-color: #f8f9fa; /* Slightly different background */
  flex-shrink: 0; /* Prevent this area from shrinking */
}

textarea {
  flex-grow: 1;
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 6px;
  resize: none; /* Disable manual resize */
  font-family: inherit;
  font-size: 1em;
  line-height: 1.5;
  min-height: 42px; /* Approx 1 row + padding */
  max-height: 150px; /* Max 4-5 rows roughly */
  overflow-y: auto; /* Show scrollbar if max-height is reached */
  transition: border-color 0.2s ease-in-out;
}

textarea:focus {
  outline: none;
  border-color: #007bff; /* Highlight on focus */
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

textarea:disabled {
  background-color: #e9ecef;
  cursor: not-allowed;
}

button {
  margin-left: 10px;
  padding: 10px 18px;
  border: none;
  background-color: #007bff;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1em;
  height: 42px; /* Match initial textarea height */
  transition: background-color 0.2s ease-in-out;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
</style>
