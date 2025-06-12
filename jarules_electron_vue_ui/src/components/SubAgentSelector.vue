<template>
  <div class="sub-agent-selector">
    <h3>Select Sub-Agents for Task</h3>
    <div v-if="isLoading" class="loading-message">
      Loading configurations...
    </div>
    <div v-else-if="error" class="error-message">
      <p>Error loading configurations:</p>
      <pre>{{ error }}</pre>
    </div>
    <div v-else-if="availableAgents.length === 0" class="no-agents-message">
      No agents available or configuration is empty.
    </div>
    <div v-else class="agent-list">
      <div v-for="agent in availableAgents" :key="agent.id" class="agent-item">
        <label>
          <input
            type="checkbox"
            :value="agent.id"
            v-model="selectedAgentIds"
            @change="emitSelection"
          />
          {{ agent.name }} (Provider: {{ agent.provider }}) - Model: {{ agent.model }}
        </label>
      </div>
    </div>
    <button @click="confirmSelection" :disabled="selectedAgentIds.length === 0">
      Confirm Agent Selection
    </button>
    <p v-if="selectedAgentIds.length > 0" class="selection-summary">
      Selected {{ selectedAgentIds.length }} agent(s).
    </p>
  </div>
</template>

<script>
import jsyaml from 'js-yaml';

export default {
  name: 'SubAgentSelector',
  data() {
    return {
      isLoading: false,
      error: null,
      availableAgents: [], // Array of { id: 'provider_model', name: 'Provider Default', provider: 'provider', model: 'model_name' }
      selectedAgentIds: [],
      rawConfig: null, // To store the parsed YAML object
    };
  },
  async mounted() {
    await this.fetchAndProcessConfiguration();
  },
  methods: {
    async fetchAndProcessConfiguration() {
      this.isLoading = true;
      this.error = null;
      this.availableAgents = [];
      try {
        const result = await window.api.getConfig(); // Assumes window.api.getConfig() is set up

        if (result && result.error) {
          this.error = `Error loading configuration: ${result.message}${result.details ? ' - ' + result.details : ''}`;
          this.isLoading = false;
          return;
        }

        const yamlString = result;
        if (yamlString && typeof yamlString === 'string') {
          this.rawConfig = jsyaml.load(yamlString);
          this.processConfig(this.rawConfig);
        } else if (typeof yamlString === 'object' && yamlString !== null) { // Already parsed
          this.rawConfig = yamlString;
          this.processConfig(this.rawConfig);
        }
         else {
          this.error = 'Failed to load configuration: No content or invalid format received.';
        }
      } catch (err) {
        console.error('Error fetching or parsing agent configuration:', err);
        this.error = `Error processing configuration: ${err.message}`;
      }
      this.isLoading = false;
    },
    processConfig(config) {
      const agents = [];
      if (!config || typeof config !== 'object') {
        this.error = 'Configuration is not a valid object.';
        return;
      }

      for (const providerKey in config) {
        if (providerKey === 'default_provider' || !config[providerKey] || typeof config[providerKey] !== 'object') {
          continue; // Skip default_provider entry or non-object provider configs
        }

        const providerConfig = config[providerKey];
        // Attempt to get a specific model or a default model
        const modelName = providerConfig.default_model || providerConfig.model || 'default';
        // Create a unique ID for the agent based on provider and model
        const agentId = `${providerKey}_${modelName.replace(/[^a-zA-Z0-9-_]/g, '_')}`; // Sanitize model name for ID

        agents.push({
          id: agentId,
          name: `${providerKey.charAt(0).toUpperCase() + providerKey.slice(1)} (Default: ${modelName})`, // e.g., Gemini (Default: gemini-pro)
          provider: providerKey,
          model: modelName,
          // You could add more details from providerConfig if needed
        });

        // If there's a list of models, you could iterate here too.
        // For simplicity, this example primarily uses the default_model.
        // Example for multiple models if structure was `models: [{name: 'x'}, {name: 'y'}]`
        // if (providerConfig.models && Array.isArray(providerConfig.models)) {
        //   providerConfig.models.forEach(modelEntry => {
        //     if (modelEntry.name && modelEntry.name !== modelName) { // Avoid duplicating the default
        //       const specificAgentId = `${providerKey}_${modelEntry.name.replace(/[^a-zA-Z0-9-_]/g, '_')}`;
        //       agents.push({
        //         id: specificAgentId,
        //         name: `${providerKey} (${modelEntry.name})`,
        //         provider: providerKey,
        //         model: modelEntry.name,
        //       });
        //     }
        //   });
        // }
      }
      this.availableAgents = agents;
      if (agents.length === 0) {
          console.warn("No agents processed from the configuration. Check llm_config.yaml structure.");
      }
    },
    emitSelection() {
      // This event is more for real-time updates if needed by a parent component
      this.$emit('agents-selection-changed', this.selectedAgentIds);
    },
    confirmSelection() {
      if (this.selectedAgentIds.length > 0) {
        // Find full agent objects for selected IDs
        const selectedFullAgents = this.availableAgents.filter(agent =>
          this.selectedAgentIds.includes(agent.id)
        );
        this.$emit('confirm-agent-selection', selectedFullAgents);
      }
    }
  },
};
</script>

<style scoped>
.sub-agent-selector {
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin: 1rem 0;
  background-color: #f9f9f9;
}

.sub-agent-selector h3 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  color: #333;
}

.loading-message, .no-agents-message {
  padding: 1rem;
  text-align: center;
  color: #555;
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
  padding: 0.5rem;
  border-radius: 3px;
  white-space: pre-wrap;
}

.agent-list {
  max-height: 200px; /* Adjust as needed */
  overflow-y: auto;
  border: 1px solid #eee;
  padding: 0.5rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.agent-item {
  padding: 0.5rem;
  border-bottom: 1px solid #f0f0f0;
}
.agent-item:last-child {
  border-bottom: none;
}

.agent-item label {
  display: block;
  cursor: pointer;
  font-size: 0.95em;
}
.agent-item input[type="checkbox"] {
  margin-right: 0.5rem;
}

.sub-agent-selector button {
  padding: 0.5rem 1rem;
  background-color: #28a745; /* Green for confirm */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.2s ease-in-out;
}

.sub-agent-selector button:hover:not(:disabled) {
  background-color: #218838;
}

.sub-agent-selector button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.selection-summary {
  margin-top: 0.75rem;
  font-size: 0.9em;
  color: #555;
}
</style>
