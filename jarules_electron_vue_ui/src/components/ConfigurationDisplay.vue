<template>
  <div class="configuration-display">
    <h2>LLM Configuration</h2>
    <div v-if="error" class="error-message">
      <p>Error loading configuration:</p>
      <pre>{{ error }}</pre>
    </div>
    <div v-else-if="typeof configurationContent === 'object'">
      <pre>{{ JSON.stringify(configurationContent, null, 2) }}</pre>
    </div>
    <div v-else>
      <pre>{{ configurationContent }}</pre>
    </div>
  </div>
</template>

<script>
import jsyaml from 'js-yaml';

export default {
  name: 'ConfigurationDisplay',
  data() {
    return {
      configurationContent: 'Loading configuration...', // Will hold the parsed object or error string
      error: null,
    };
  },
  async mounted() {
    await this.fetchConfiguration();
  },
  methods: {
    async fetchConfiguration() {
      try {
        this.error = null;
        // In Electron, the getConfig function might return the raw data or an object with an error property
        const result = await window.api.getConfig();

        // Check if the main process returned an error object
        if (result && result.error) {
          console.error('Error from main process getConfig:', result.message, result.details);
          this.configurationContent = `Error loading configuration: ${result.message}`;
          this.error = `Error loading configuration: ${result.message}${result.details ? ' - ' + result.details : ''}`;
          return;
        }

        const yamlString = result; // Assuming result is the yaml string if not an error object

        if (yamlString && typeof yamlString === 'string') {
          this.configurationContent = jsyaml.load(yamlString);
        } else if (yamlString) { // It's not a string, but not an error object from main, could be already parsed? Or unexpected.
          // This case handles if getConfig for some reason returns already parsed JSON or non-string data.
          // For now, we assume it's an unexpected format if not a string.
          console.warn('Received non-string data from getConfig, attempting to display as is or use directly if object:', yamlString);
          if (typeof yamlString === 'object') {
            this.configurationContent = yamlString; // If it's an object, use it directly
          } else {
            this.configurationContent = 'Failed to load configuration: Invalid format received.';
            this.error = 'Failed to load configuration: Invalid format received.';
          }
        } else { // Null or undefined yamlString
          this.configurationContent = 'Failed to load configuration: No content received.';
          this.error = 'Failed to load configuration: No content received.';
        }
      } catch (err) { // Catches errors from jsyaml.load or other unexpected issues
        console.error('Error fetching or parsing configuration:', err);
        this.configurationContent = `Error loading configuration: ${err.message}`;
        this.error = `Error loading configuration: ${err.message}`;
      }
    }
  }
};
</script>

<style scoped>
.configuration-display {
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin: 1rem;
}
pre {
  background-color: #f5f5f5;
  padding: 0.5rem;
  border-radius: 4px;
  white-space: pre-wrap; /* Allow text wrapping */
  word-break: break-all; /* Break long words */
}
.error-message {
  color: red;
  border: 1px solid red;
  padding: 0.5rem;
  margin-bottom: 1rem;
}
.error-message pre {
  color: red;
  background-color: #ffe0e0;
}
</style>
