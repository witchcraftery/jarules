<template>
  <div class="configuration-display">
    <h2>LLM Configuration</h2>
    <div v-if="isLoading" class="loading-message">
      Loading configuration... Please wait.
    </div>
    <div v-else-if="error" class="error-message">
      <p><strong>Error Loading Configuration:</strong></p>
      <pre>{{ error }}</pre>
    </div>
    <div v-else-if="configurationContent && typeof configurationContent === 'object' && Object.keys(configurationContent).length > 0" class="structured-config-view">
      <ConfigNodeViewer :node-data="configurationContent" node-title=""/>
    </div>
    <div v-else-if="configurationContent && typeof configurationContent === 'object' && Object.keys(configurationContent).length === 0" class="no-config-message">
        Configuration is empty or not structured as expected.
    </div>
    <div v-else class="no-config-message">
      No configuration data loaded or format is unexpected.
      <pre v-if="configurationContent">{{ configurationContent }}</pre>
    </div>
  </div>
</template>

<script>
import jsyaml from 'js-yaml';
import ConfigNodeViewer from './ConfigNodeViewer.vue';

export default {
  name: 'ConfigurationDisplay',
  components: {
    ConfigNodeViewer,
  },
  data() {
    return {
      configurationContent: null,
      error: null,
      isLoading: false,
    };
  },
  async mounted() {
    await this.fetchConfiguration();
  },
  methods: {
    async fetchConfiguration() {
      this.isLoading = true;
      this.error = null;
      this.configurationContent = null;
      try {
        const result = await window.api.getConfig();

        if (result && result.error) {
          console.error('Error from main process getConfig:', result.message, result.details);
          this.error = `Failed to retrieve configuration from the backend. Details: ${result.message}${result.details ? ' - ' + result.details : ''}`;
          this.isLoading = false;
          return;
        }

        const yamlString = result;
        if (yamlString && typeof yamlString === 'string') {
          this.configurationContent = jsyaml.load(yamlString);
        } else if (typeof yamlString === 'object' && yamlString !== null) {
          this.configurationContent = yamlString; // Already parsed
        } else if (!yamlString) { // Handles null or empty string from backend
          this.error = 'No configuration content was returned from the backend. The configuration file might be empty or missing.';
        }
         else { // Fallback for unexpected types
          this.error = 'Failed to load configuration: Invalid or unexpected format received from backend.';
          console.warn('Unexpected configuration format:', yamlString);
        }
      } catch (err) { // Catches errors from jsyaml.load or other synchronous issues
        console.error('Error parsing configuration YAML or other client-side issue:', err);
        this.error = `Error processing configuration data: ${err.message}. Please check YAML syntax if the file was loaded.`;
      }
      this.isLoading = false;
    }
  }
};
</script>

<style scoped>
.configuration-display {
  padding: 1rem 1.5rem; /* Increased padding */
  border: 1px solid #dee2e6; /* Softer border */
  border-radius: 6px; /* Slightly more rounded */
  margin: 1rem;
  background-color: #f8f9fa;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Subtle shadow */
}
.configuration-display h2 {
    margin-top: 0;
    margin-bottom: 1.2rem; /* More space below heading */
    color: #343a40;
    border-bottom: 1px solid #e9ecef; /* Lighter border */
    padding-bottom: 0.8rem; /* More padding for heading */
    font-size: 1.4em; /* Slightly larger heading */
}

.loading-message, .no-config-message {
  padding: 1.5rem; /* More padding */
  text-align: center;
  color: #6c757d;
  font-style: italic;
  background-color: #fff; /* White background for these messages */
  border-radius: 4px;
  border: 1px dashed #ced4da;
}
.no-config-message pre {
    background-color: #e9ecef;
    padding: 0.75rem;
    border-radius: 4px;
    margin-top: 0.75rem;
    font-size: 0.9em;
    text-align: left; /* Align pre content left */
    white-space: pre-wrap;
    word-break: break-all;
}

.error-message {
  color: #721c24;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  padding: 1rem 1.5rem; /* More padding */
  margin-bottom: 1rem;
  border-radius: .3rem; /* Consistent rounding */
}
.error-message strong {
    display: block;
    margin-bottom: .5rem;
    font-size: 1.1em;
}
.error-message pre {
  color: #721c24; /* Ensure pre text matches error color */
  background-color: transparent;
  padding: 0;
  margin-top: .25rem;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 0.95em;
}

.structured-config-view {
  font-size: 1em; /* Base font size for config view */
  line-height: 1.6;
  padding: 0.5rem;
  background-color: #ffffff; /* White background for the actual config tree */
  border-radius: 4px;
  border: 1px solid #e9ecef;
}
</style>
