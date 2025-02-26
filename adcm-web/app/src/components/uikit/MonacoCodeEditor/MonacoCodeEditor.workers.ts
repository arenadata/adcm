import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
// eslint-disable-next-line import-x/default
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import YamlWorker from './yaml.worker.js?worker';

// todo: minimize by following
// https://github.com/microsoft/monaco-editor/blob/main/samples/browser-esm-webpack-small/index.js

self.MonacoEnvironment = {
  // biome-ignore lint/suspicious/noExplicitAny:
  getWorker(_: any, label: string) {
    switch (label) {
      // Handle other cases
      case 'json':
        return new jsonWorker();
      case 'yaml':
        return new YamlWorker();
      default:
        console.warn(`Unknown label ${label}`);
        return new editorWorker();
    }
  },
};
