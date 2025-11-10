<template>
  <div class="modal-backdrop" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Results for {{ agent.name }}</h3>
        <button class="close-button" @click="close">&times;</button>
      </div>
      <div class="modal-body">
        <div class="summary-section">
          <h4>Solution Summary</h4>
          <div v-if="summaryContent" class="markdown-content" v-html="renderedMarkdown"></div>
          <p v-else>No summary was provided by this agent.</p>
        </div>
        <div class="files-section">
          <h4>Key Files</h4>
          <ul v-if="keyFiles.length > 0">
            <li v-for="file in keyFiles" :key="file" @click="viewFileContent(file)" class="file-item">
              {{ file }}
            </li>
          </ul>
          <p v-else>No key files were listed by this agent.</p>
        </div>
        <div v-if="activeFile" class="file-content-viewer">
          <h5>Content of {{ activeFile.path }}</h5>
          <pre><code>{{ activeFile.content }}</code></pre>
        </div>
      </div>
      <div class="modal-footer">
        <button class="action-button" @click="downloadZip">Download as Zip</button>
        <button class="action-button" @click="close">Close</button>
      </div>
    </div>
  </div>
</template>

<script>
import { marked } from 'marked';

export default {
  name: 'ResultDetailsModal',
  props: {
    agent: {
      type: Object,
      required: true
    },
    runId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      summaryContent: '',
      keyFiles: [],
      activeFile: null, // { path: '...', content: '...' }
    };
  },
  computed: {
    renderedMarkdown() {
      return this.summaryContent ? marked(this.summaryContent) : '';
    }
  },
  methods: {
    close() {
      this.$emit('close');
    },
    async fetchDetails() {
        this.summaryContent = this.agent.resultSummary || 'Loading summary...';
        this.keyFiles = this.agent.keyFilePaths || [];
    },
    async viewFileContent(filePath) {
      try {
        const result = await window.api.getAgentFileContent({
          runId: this.runId,
          agentId: this.agent.id,
          filePath: filePath
        });
        if (result.success) {
          this.activeFile = { path: filePath, content: result.content };
        } else {
          this.activeFile = { path: filePath, content: `Error loading file: ${result.error}` };
        }
      } catch (error) {
        this.activeFile = { path: filePath, content: `IPC Error: ${error.message}` };
      }
    },
    async downloadZip() {
        try {
            const result = await window.api.triggerAgentZipCreation({
                runId: this.runId,
                agentId: this.agent.id
            });
            if (result.success) {
                // The main process will handle the download dialog.
                // We just need to tell it to start.
                alert(`Preparing to download ${result.filename}. Your download will start shortly.`);
            } else {
                alert(`Failed to create zip file: ${result.error}`);
            }
        } catch (error) {
            alert(`Error triggering download: ${error.message}`);
        }
    }
  },
  mounted() {
    this.fetchDetails();
  }
};
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  width: 80%;
  max-width: 900px;
  height: 80vh;
  display: flex;
  flex-direction: column;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}
.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
}
.modal-body {
  flex-grow: 1;
  overflow-y: auto;
  padding-top: 15px;
}
.summary-section, .files-section {
  margin-bottom: 20px;
}
.markdown-content {
  border: 1px solid #eee;
  padding: 10px;
  border-radius: 4px;
  background-color: #f9f9f9;
}
.file-item {
  cursor: pointer;
  padding: 5px;
  border-radius: 3px;
  transition: background-color 0.2s;
}
.file-item:hover {
  background-color: #e9ecef;
}
.file-content-viewer {
  margin-top: 15px;
  border-top: 1px solid #eee;
  padding-top: 15px;
}
.file-content-viewer pre {
  background-color: #2b2b2b;
  color: #f8f8f2;
  padding: 15px;
  border-radius: 5px;
  max-height: 400px;
  overflow: auto;
}
.modal-footer {
  border-top: 1px solid #ddd;
  padding-top: 15px;
  text-align: right;
}
.action-button {
  padding: 8px 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.action-button:hover {
  background-color: #0056b3;
}
</style>
