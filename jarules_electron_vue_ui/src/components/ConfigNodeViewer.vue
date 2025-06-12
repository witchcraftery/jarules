<template>
  <div class="config-node-viewer">
    <strong v-if="nodeTitle" class="node-title">{{ formatKey(nodeTitle) }}:</strong>
    <div v-if="isObject(nodeData)" class="config-object">
      <ul>
        <li v-for="(value, key) in nodeData" :key="key">
          <ConfigNodeViewer :node-data="value" :node-title="key" />
        </li>
      </ul>
    </div>
    <div v-else-if="isArray(nodeData)" class="config-array">
      <strong v-if="!nodeTitle && isArray(nodeData)" class="node-title array-title">Array Items:</strong>
      <ul>
        <li v-for="(item, index) in nodeData" :key="index">
          <ConfigNodeViewer :node-data="item" :node-title="String(index)" />
        </li>
      </ul>
    </div>
    <div v-else class="config-value">
      {{ displayValue(nodeData) }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConfigNodeViewer',
  props: {
    nodeData: {
      required: true,
      // Can be Object, Array, String, Number, Boolean, null
    },
    nodeTitle: {
      type: String,
      default: '',
    },
  },
  methods: {
    isObject(data) {
      return typeof data === 'object' && data !== null && !Array.isArray(data);
    },
    isArray(data) {
      return Array.isArray(data);
    },
    formatKey(key) {
      // Only format if it's not a numeric index from an array
      if (isNaN(Number(key))) {
        let formatted = key.replace(/_/g, ' ');
        formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
        return formatted;
      }
      return `Item ${Number(key) + 1}`; // For array items, use 1-based indexing for display
    },
    displayValue(value) {
      if (value === null) return 'Not set (null)';
      if (typeof value === 'boolean') return value ? 'Enabled' : 'Disabled';

      // Special handling for API keys for security
      if (this.nodeTitle) {
        const titleLower = this.nodeTitle.toLowerCase();
        if ((titleLower.includes('api') && titleLower.includes('key')) || titleLower.includes('token') || titleLower.includes('secret')) {
            if (typeof value === 'string' && value.length > 4) {
                if (value.startsWith('ENV_') || value.includes('_API_KEY') || value.toUpperCase() === value || value.startsWith('${') || value.startsWith('{{')) {
                    return `Loaded from environment variable (e.g., ${value})`;
                }
                return `********${value.slice(-4)} (Likely loaded from environment)`;
            }
        }
      }
      return value;
    }
  },
};
</script>

<style scoped>
.config-node-viewer {
  padding-left: 10px;
  margin-bottom: 6px;
  line-height: 1.5;
}

.node-title {
  color: #35495e; /* Dark blue-grey */
  font-weight: bold;
}
.array-title { /* Specific title for root arrays if nodeTitle is not passed */
    display: block;
    margin-bottom: 4px;
}

.config-object ul,
.config-array ul {
  list-style-type: none;
  padding-left: 20px;
  margin-top: 4px;
  border-left: 2px dashed #bdc3c7; /* Light grey */
}

.config-object li,
.config-array li {
  margin-bottom: 5px;
}

.config-value {
  display: inline; /* Keep simple values on the same line as title */
  margin-left: 8px;
  color: #2c3e50; /* Slightly lighter than title */
  word-break: break-all; /* Break long strings */
}
</style>
