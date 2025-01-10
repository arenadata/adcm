import type React from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import MonacoCodeEditor from './MonacoCodeEditor';
import ConfigWithSchema from './MonacoCodeEditor.multipleInstances';

type Story = StoryObj<typeof MonacoCodeEditor>;

export default {
  title: 'uikit/MonacoCodeEditor',
  component: MonacoCodeEditor,
  argTypes: {},
} as Meta<typeof MonacoCodeEditor>;

/**
 * Easy Editor without validation, only JSON
 */
const MonacoCodeEditorExample: React.FC = () => {
  return (
    <MonacoCodeEditor
      uri="http://someurl/foo"
      text={JSON.stringify({ field1: 123, field2: 'some text' }, null, 2)}
      language="json"
    />
  );
};

export const MonacoCodeEditorStory: Story = {
  name: 'Easy Editor',
  render: () => {
    return (
      <div style={{ height: '500px' }}>
        <MonacoCodeEditorExample />
      </div>
    );
  },
};

/**
 * Easy Editor without validation, can to switch languages
 */
const MonacoCodeEditorSwitchLanguages: React.FC = () => {
  return (
    <ConfigWithSchema
      initLanguage="json"
      initConfig={{
        someField: 123,
        someField2: 'abs word',
      }}
      modelUri="http://someurl/foo"
    />
  );
};

export const MonacoCodeEditorSwitchLanguagesStory: Story = {
  name: 'Switch Languages',
  render: () => {
    return (
      <div style={{ height: '500px' }}>
        <MonacoCodeEditorSwitchLanguages />
      </div>
    );
  },
};

const configSchema1 = {
  type: 'object',
  title: 'Primary configuration',
  required: ['someField'],
  properties: {
    someField: {
      type: 'number',
    },
    someField2: {
      type: 'string',
    },
  },
  additionalProperties: false,
};

const configSchema2 = {
  type: 'object',
  title: 'Secondary configuration',
  required: ['name'],
  properties: {
    name: {
      type: 'string',
    },
    description: {
      type: 'string',
    },
  },
  additionalProperties: false,
};

/**
 * Validate by JSON-schema, can to switch languages
 */
const MonacoCodeEditorValidation: React.FC = () => {
  return (
    <ConfigWithSchema
      initLanguage="json"
      initConfig={{
        someField: 123,
        someField2: 'abs word',
        someField3: 456,
      }}
      initSchema={configSchema1}
      modelUri="http://someurl/text1"
    />
  );
};

export const MonacoCodeEditorValidationStory: Story = {
  name: 'Validation with JSON schema',
  render: () => {
    return <MonacoCodeEditorValidation />;
  },
};

/**
 * Validate by JSON-schema, two separate editors, can to switch languages
 */
const MonacoCodeEditorTwoEditors: React.FC = () => {
  return (
    <div>
      <h2>Editor 1:</h2>
      <br />
      <ConfigWithSchema
        initLanguage="json"
        initConfig={{
          someField: 123,
          someField2: 'abs word',
          someField3: 456,
        }}
        initSchema={configSchema1}
        modelUri="http://someurl/text1"
      />
      <br />
      <br />
      <br />
      <h2>Editor 2:</h2>
      <br />
      <ConfigWithSchema
        initLanguage="json"
        initConfig={{
          someField5: 'another words',
        }}
        initSchema={configSchema2}
        modelUri="http://someurl/text2"
      />
    </div>
  );
};

export const MonacoCodeEditorTwoEditorsStory: Story = {
  name: 'Two Editors + Validation',
  render: () => {
    return <MonacoCodeEditorTwoEditors />;
  },
};
