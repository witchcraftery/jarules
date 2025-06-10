// jarules_electron_vue_ui/src/components/__tests__/ConfigurationDisplay.spec.js
import { mount } from '@vue/test-utils';
import { describe, it, expect, vi, beforeEach } from 'vitest'; // Or Jest equivalents
import ConfigurationDisplay from '../ConfigurationDisplay.vue';
import jsyaml from 'js-yaml';

// Mock the global window.api.getConfig
// Ensure this setup is compatible with the test environment (e.g., JSDOM for Vitest/Jest)
if (typeof global.window === 'undefined') {
  global.window = {};
}
global.window.api = {
  getConfig: vi.fn(),
  ...(global.window.api || {}) // Preserve other api functions if any
};


describe('ConfigurationDisplay.vue', () => {
  beforeEach(() => {
    // Reset mocks before each test
    window.api.getConfig.mockReset();
  });

  it('renders loading state initially', () => {
    window.api.getConfig.mockReturnValueOnce(new Promise(() => {})); // Keep it pending, effectively a never-resolving promise
    const wrapper = mount(ConfigurationDisplay);
    expect(wrapper.text()).toContain('Loading configuration...');
  });

  it('fetches and displays configuration on mount', async () => {
    const mockConfig = { gemini: { api_key: 'GEMINI_API_KEY' }, default_provider: 'gemini' };
    const yamlString = jsyaml.dump(mockConfig);
    window.api.getConfig.mockResolvedValueOnce(yamlString);

    const wrapper = mount(ConfigurationDisplay);
    // Wait for promises to resolve and component to update
    await new Promise(resolve => setTimeout(resolve, 0)); // Allow mounted and fetchConfiguration to run
    await wrapper.vm.$nextTick(); // Allow Vue to re-render

    // Check if JSON stringified output is present
    expect(wrapper.text()).toContain('"gemini":');
    expect(wrapper.text()).toContain('"api_key": "GEMINI_API_KEY"');
    expect(wrapper.text()).toContain('"default_provider": "gemini"');
    expect(wrapper.find('.error-message').exists()).toBe(false);
  });

  it('displays error message if config loading via IPC fails (rejected promise)', async () => {
    window.api.getConfig.mockRejectedValueOnce(new Error('IPC Failed to load'));
    const wrapper = mount(ConfigurationDisplay);
    await new Promise(resolve => setTimeout(resolve, 0));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.error-message').exists()).toBe(true);
    expect(wrapper.text()).toContain('Error loading configuration: IPC Failed to load');
  });

  it('displays error message if getConfig returns an error object', async () => {
    const errorResponse = { error: true, message: "File not found", details: "config/llm_config.yaml could not be read." };
    window.api.getConfig.mockResolvedValueOnce(errorResponse);

    const wrapper = mount(ConfigurationDisplay);
    await new Promise(resolve => setTimeout(resolve, 0));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.error-message').exists()).toBe(true);
    expect(wrapper.text()).toContain(`Error loading configuration: ${errorResponse.message}`);
    expect(wrapper.text()).toContain(errorResponse.details);
  });


  it('displays error message if config content is null', async () => {
    window.api.getConfig.mockResolvedValueOnce(null);
    const wrapper = mount(ConfigurationDisplay);
    await new Promise(resolve => setTimeout(resolve, 0));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.error-message').exists()).toBe(true);
    expect(wrapper.text()).toContain('Failed to load configuration: No content received.');
  });

  it('displays error message if YAML parsing fails', async () => {
    const invalidYamlString = "gemini: api_key: 'GEMINI_API_KEY"; // Missing quote
    window.api.getConfig.mockResolvedValueOnce(invalidYamlString);

    const wrapper = mount(ConfigurationDisplay);
    await new Promise(resolve => setTimeout(resolve, 0));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.error-message').exists()).toBe(true);
    // The exact error message from js-yaml can be brittle to test, so check for a part of it.
    // Example: "YAMLException: unexpected end of the stream within a single quoted scalar at line 1, column 20:"
    // Or "StringParseException: unexpected end of the stream within a single quoted scalar" for older js-yaml
    expect(wrapper.text()).toContain('Error loading configuration:');
    // More robustly, check that it's not trying to display the invalid YAML as an object
    expect(wrapper.text()).not.toContain('"gemini":');
  });
});
