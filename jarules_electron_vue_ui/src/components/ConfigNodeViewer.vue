<template>
  <div class="config-node-viewer">
    <strong v-if="nodeTitle" :class="['node-title', getNodeTitleClass(nodeTitle)]">{{ formatKey(nodeTitle) }}:</strong>
    <div v-if="isObject(nodeData)" class="config-object">
      <ul>
        <li v-for="(value, key) in nodeData" :key="key">
          <ConfigNodeViewer :node-data="value" :node-title="key" />
        </li>
      </ul>
    </div>
    <div v-else-if="isArray(nodeData)" class="config-array">
      <strong v-if="nodeTitle && formatKey(nodeTitle).toLowerCase().includes('items')" class="node-title array-title">
        {{ formatKey(nodeTitle) }}:
      </strong>
      <strong v-else-if="!nodeTitle" class="node-title array-title">Array Items:</strong>
      <ul>
        <li v-for="(item, index) in nodeData" :key="index">
          <ConfigNodeViewer :node-data="item" :node-title="String(index)" />
        </li>
      </ul>
    </div>
    <div v-else :class="['config-value', getValueClass(nodeData)]">
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
      // Use the formatted key for checking, not the raw nodeTitle prop directly
      const currentFormattedKey = this.nodeTitle ? this.formatKey(this.nodeTitle).toLowerCase() : '';
      if (currentFormattedKey) {
        if ((currentFormattedKey.includes('api') && currentFormattedKey.includes('key')) || currentFormattedKey.includes('token') || currentFormattedKey.includes('secret')) {
            if (typeof value === 'string' && value.length > 0) {
                if (value.startsWith('ENV_') || value.includes('_API_KEY') || value.toUpperCase() === value || value.startsWith('${') || value.startsWith('{{')) {
                    return `Loaded from environment variable (e.g., ${value})`;
                }
                if (value.length > 4) return `********${value.slice(-4)} (Masked)`;
                return "**** (Masked)";
            }
        }
      }
      return value;
    },
    // Method to provide class for value styling based on type
    getValueClass(value) {
      if (typeof value === 'boolean') return 'config-value-boolean';
      if (value === null) return 'config-value-null';
      return '';
    },
    // Method to provide class for node title (key)
    getNodeTitleClass(rawTitle) {
      // Use the formatted key for class determination
      const formattedTitle = this.formatKey(rawTitle);
      if (formattedTitle === 'Id') {
        // This will make any key that formats to "Id" prominent.
        // This is a broad approach; more specific context (e.g. parent) would need prop drilling or event emitting.
        return 'config-id-title';
      }
      return '';
    }
  },
};
</script>

<style scoped>
.config-node-viewer {
  padding-left: 10px; /* Base indentation for all nodes */
  margin-bottom: 8px; /* Increased spacing between nodes */
  line-height: 1.6; /* Slightly increased line height for readability */
}

.node-title {
  color: #35495e; /* Dark blue-grey for standard keys */
  font-weight: bold;
  margin-right: 6px; /* Space between title/key and colon/value */
  display: inline-block; /* Allows margin-bottom if it becomes block later */
}

/* Special styling for titles that act as headers for config items, specifically 'Id' */
.node-title.config-id-title {
  font-size: 1.1em; /* Make 'Id' fields slightly larger */
  color: #0056b3; /* Darker, more prominent blue */
  display: block; /* Make 'Id' title take its own line */
  margin-top: 15px; /* Add significant space above a new 'Id' field, suggesting a new item */
  margin-bottom: 6px; /* Space below the 'Id' title */
  padding-bottom: 4px; /* Padding for the border */
  border-bottom: 1px solid #e0e0e0; /* Separator line below 'Id' */
}
/* Ensure the first 'Id' in a list doesn't have excessive top margin */
.config-object > ul > li:first-child > .config-node-viewer > .node-title.config-id-title,
.config-array > ul > li:first-child > .config-node-viewer > .node-title.config-id-title {
  margin-top: 5px; /* Reduced top margin for the very first 'Id' in a list */
}


.array-title { /* Styling for explicit "Array Items:" title */
    display: block;
    margin-bottom: 5px; /* Space below "Array Items:" */
    font-size: 1.05em;
    color: #17a2b8; /* Info color for array titles */
}

.config-object ul,
.config-array ul {
  list-style-type: none;
  padding-left: 25px; /* Indentation for nested lists */
  margin-top: 5px; /* Space above the list itself */
  border-left: 2px solid #dfe4ea; /* Softer border color for visual grouping */
}

.config-object li,
.config-array li {
  margin-bottom: 6px; /* Spacing between individual list items */
  padding-top: 3px; /* Padding within each list item */
}

/* Attempt to visually separate items in the main 'llm_configs' array */
/* This targets list items that are direct children of a .config-array's ul.
   It's a general approach for items in arrays.
   If 'llm_configs' is the first array rendered, its items will get this style.
*/
.config-array > ul > li {
  /* border-top: 1px solid #e9ecef; */ /* Removed this, as config-id-title provides better separation */
  /* padding-top: 10px; */
  /* margin-top: 5px; */ /* Using config-id-title's margin-top for separation */
}
/* .config-array > ul > li:first-child {
  border-top: none;
  margin-top: 0;
  padding-top: 3px;
} */


.config-value {
  display: inline-block; /* Allows padding and better control than 'inline' */
  margin-left: 5px; /* Space from the key/title */
  color: #2c3e50; /* Standard value color */
  word-break: break-all; /* Prevent long values from breaking layout */
  vertical-align: top; /* Align with the top of the key if key is block/inline-block */
}

/* Specific styling for boolean and null values for better visual distinction */
.config-value-boolean,
.config-value-null {
  font-style: italic;
  color: #5a6268; /* Greyish color, stands out from regular string/number values */
}
</style>
