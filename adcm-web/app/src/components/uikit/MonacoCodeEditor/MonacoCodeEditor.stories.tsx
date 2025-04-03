import { useCallback, useRef } from 'react';
import MonacoCodeEditor from './MonacoCodeEditor';
import type { Meta, StoryObj } from '@storybook/react';
import { schema, jsonText, yamlText, mappingSchema, mappingText } from './MonacoCodeEditor.stories.constants';
import yaml from 'yaml';
import { type IPosition, type IRange, type ITextModel, monaco } from './MonacoCodeEditor.types';
import { exposeAdditionalInfo, setCustomMarkers, resetCustomMarkers } from './MonacoCodeEditor.utils';

type Story = StoryObj<typeof MonacoCodeEditor>;

export default {
  title: 'uikit/MonacoCodeEditor',
  component: MonacoCodeEditor,
  argTypes: {},
} as Meta<typeof MonacoCodeEditor>;

const MonacoCodeEditorJsonExample = () => {
  const model = useRef({});

  const handleChange = useCallback((value: string) => {
    try {
      const parsed = JSON.parse(value);
      model.current = parsed;
    } catch (e) {
      console.error('json parse error', e);
    }
  }, []);

  return (
    <MonacoCodeEditor
      uri="http://myserver/foo.json"
      language="json"
      text={jsonText}
      schema={schema}
      onChange={handleChange}
    />
  );
};

export const MonacoCodeEditorJsonStory: Story = {
  render: () => {
    return (
      <div style={{ height: '500px' }}>
        <MonacoCodeEditorJsonExample />
      </div>
    );
  },
};

const MonacoCodeEditorJsonWithCustomErrorExample = () => {
  const config = useRef({});

  const handleUnmount = () => {
    resetCustomMarkers('custom');
  };

  const handleChange = useCallback((value: string, model: ITextModel) => {
    try {
      const parsed = JSON.parse(value);
      config.current = parsed;

      exposeAdditionalInfo(model);
      const markers = [];
      markers.push({
        message: 'Some custom error',
        severity: monaco.MarkerSeverity.Error,
        startLineNumber: 1,
        startColumn: 1,
        endLineNumber: 1,
        endColumn: 2,
        owner: 'custom',
        resource: model.uri,
      });

      setCustomMarkers(model, 'custom', markers);
    } catch (e) {
      console.error('json parse error', e);
    }
  }, []);

  return (
    <MonacoCodeEditor
      uri="http://myserver/foo.json"
      language="json"
      text={jsonText}
      schema={schema}
      validate={false}
      onChange={handleChange}
      onUnmount={handleUnmount}
    />
  );
};

export const MonacoCodeEditorJsonWithCustomErrorStory: Story = {
  render: () => {
    return (
      <div style={{ height: '500px' }}>
        <MonacoCodeEditorJsonWithCustomErrorExample />
      </div>
    );
  },
};

const MonacoCodeEditorYamlExample = () => {
  const model = useRef({});

  const handleChange = useCallback((value: string) => {
    try {
      const parsed = yaml.parse(value);
      model.current = parsed as string;
    } catch (e) {
      console.error('yaml parse error', e);
    }
  }, []);

  return (
    <MonacoCodeEditor
      uri="http://myserver/foo.yaml"
      language="yaml"
      text={yamlText}
      schema={schema}
      onChange={handleChange}
    />
  );
};

export const MonacoCodeEditorYamlStory: Story = {
  render: () => {
    return (
      <div style={{ height: '500px' }}>
        <MonacoCodeEditorYamlExample />
      </div>
    );
  },
};

const generateServicesProposals = (range: IRange) => {
  return [
    {
      label: 'service 1',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'Service 1',
      insertText: 'service 1:',
      range: range,
    },
    {
      label: 'service 2',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'Service 2',
      insertText: 'service 2:',
      range: range,
    },
  ];
};

const generateComponentsProposals = (range: IRange) => {
  return [
    {
      label: 'component 1',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'Component 1 of Service 1',
      insertText: 'component 1:',
      range: range,
    },
    {
      label: 'component 2',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'Component 2 of Service 1',
      insertText: 'component 2:',
      range: range,
    },
    {
      label: 'component 3',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'Component 3 of Service 1',
      insertText: 'component 3:',
      range: range,
    },
  ];
};

const generateHostsProposals = (range: IRange) => {
  return [
    {
      label: 'all',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'All hosts',
      insertText: `- host 1
- host 2
- host 3`,
      range: range,
    },
    {
      label: 'host 1',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'Host 1',
      insertText: '- host 1',
      range: range,
    },
    {
      label: 'host 2',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'Host 2',
      insertText: '- host 2',
      range: range,
    },
    {
      label: 'host 3',
      kind: monaco.languages.CompletionItemKind.Function,
      documentation: 'Host 3',
      insertText: '- host 3',
      range: range,
    },
  ];
};

const MonacoCodeEditorMappingExample = () => {
  const model = useRef({});

  const handleChange = useCallback((value: string) => {
    try {
      const parsed = yaml.parse(value);
      model.current = parsed as string;
    } catch (e) {
      console.error('mapping parse error', e);
    }
  }, []);

  const handleAutocomplete = useCallback((model: ITextModel, position: IPosition) => {
    // find out if we are completing a property in the 'dependencies' object.
    const line = model.getValueInRange({
      startLineNumber: position.lineNumber,
      startColumn: 1,
      endLineNumber: position.lineNumber,
      endColumn: position.column,
    });

    const matches = line.match(/^[\s]*/g);
    if (matches === null) {
      return [];
    }

    const word = model.getWordUntilPosition(position);
    const spacesCount = matches[0].length;

    const range = {
      startLineNumber: position.lineNumber,
      endLineNumber: position.lineNumber,
      startColumn: word.startColumn,
      endColumn: word.endColumn,
    };

    switch (spacesCount) {
      case 2:
        return generateServicesProposals(range);
      case 4:
        return generateComponentsProposals(range);
      case 6:
        return generateHostsProposals(range);
      default:
        return [];
    }
  }, []);

  return (
    <MonacoCodeEditor
      uri="http://myserver/mapping.yaml"
      language="yaml"
      text={mappingText}
      schema={mappingSchema}
      onChange={handleChange}
      onAutoComplete={handleAutocomplete}
    />
  );
};

export const MonacoCodeEditorMappingStory: Story = {
  render: () => {
    return (
      <div style={{ height: '500px' }}>
        <MonacoCodeEditorMappingExample />
      </div>
    );
  },
};
