<template>
  <div class="task-definition-input">
    <h3>Define Task for Parallel Agents</h3>
    <textarea
      v-model="taskDescription"
      placeholder="Enter the detailed task description or prompt here..."
      rows="5"
    ></textarea>
    <button @click="submitTask" :disabled="!taskDescription.trim()">
      Submit Task Definition
    </button>
  </div>
</template>

<script>
export default {
  name: 'TaskDefinitionInput',
  data() {
    return {
      taskDescription: '',
    };
  },
  methods: {
    submitTask() {
      if (this.taskDescription.trim()) {
        this.$emit('submit-task', this.taskDescription.trim());
        // Optionally clear after submit, or let parent handle
        // this.taskDescription = '';
      }
    },
  },
};
</script>

<style scoped>
.task-definition-input {
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin: 1rem 0; /* Adjust margin as needed for layout */
  background-color: #f9f9f9;
}

.task-definition-input h3 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  color: #333;
}

.task-definition-input textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-bottom: 0.75rem;
  font-family: inherit;
  font-size: 1em;
  resize: vertical; /* Allow vertical resizing */
}

.task-definition-input button {
  padding: 0.5rem 1rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.2s ease-in-out;
}

.task-definition-input button:hover:not(:disabled) {
  background-color: #0056b3;
}

.task-definition-input button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
</style>
