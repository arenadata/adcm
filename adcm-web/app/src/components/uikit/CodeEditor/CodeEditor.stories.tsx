/* eslint-disable spellcheck/spell-checker */
import { useState } from 'react';
import CodeEditor from './CodeEditor';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof CodeEditor>;

const jsonText = `
{
  some_object: {
    some_string: "lorem ipsum",
    some_number: 123,
    some_boolean: true,
  },
  some_array: [{
    f1: 123,
    f2: "qwert",
  }, {
    f1: 456,
    f2: "asdfg",
  }],
}
`;

export default {
  title: 'uikit/CodeEditor',
  component: CodeEditor,
  argTypes: {
    language: {
      description: 'highlighter language',
      defaultValue: 'json',
    },
    isSecret: {
      defaultValue: false,
    },
  },
} as Meta<typeof CodeEditor>;

const CodeEditorExample = ({ ...args }) => {
  const [code, setCode] = useState(args.code);
  return (
    <div style={{ height: '500px', maxWidth: '1100px' }}>
      <CodeEditor code={code} language={args.language} isSecret={args.isSecret} onChange={setCode} />
    </div>
  );
};

export const CodeEditorStory: Story = {
  args: {
    language: 'json',
    code: jsonText,
    isSecret: false,
  },
  render: (args) => {
    return <CodeEditorExample {...args} />;
  },
};
