<template>
  <div id="app-container">
    <h1>{{ message }}</h1>
    <p>Electron version: <span id="electron-version"></span></p>
    <p>Node version: <span id="node-version"></span></p>
    <p>Chrome version: <span id="chrome-version"></span></p>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const message = ref('Hello from JaRules (Electron + Vue.js + Vite!)');
</script>

<style scoped>
#app-container {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
h1 {
  color: #42b983;
}
</style>
