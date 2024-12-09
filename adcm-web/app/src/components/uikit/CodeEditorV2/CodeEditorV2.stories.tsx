/* eslint-disable spellcheck/spell-checker */
import { useState } from 'react';
import CodeEditorV2 from './CodeEditorV2';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof CodeEditorV2>;

const jsonText = `{
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
  more_data: {
    key1: "value1",
    key2: "value2",
    key3: "value3",
    key4: "value4",
    more_data_for_the_god_of_data: {
      someKey: "someValue",
      someKey1: "someValue1",
      someKey2: "someValue2",
      someKey3: "someValue3",
      someKey4: "someValue4",
      oneMoreArray: [
        "string",
        1,
        2,
        3,
        4,
        "another string",
        "long strings ========================================================================================================================================================================================================================================================================================================================================================================================================================================================",
        "long strings ========================================================================================================================================================================================================================================================================================================================================================================================================================================================",
      ],
    },
  },
  turtle: "

                                                               ___-------___
                                                           _-~~             ~~-_
                                                        _-~                    /~-_
                                     /^\\__/^\\         /~  \\                   /    \\
                                   /|  O|| O|        /      \\_______________/        \\
                                  | |___||__|      /       /                \\          \\
                                  |          \\    /      /                    \\          \\
                                  |   (_______) /______/                        \\_________ \\
                                  |         / /         \\                      /            \\
                                   \\         \\^\\\\         \\                  /               \\     /
                                     \\         ||           \\______________/      _-_       //\\__//
                                       \\       ||------_-~~-_ ------------- \\ --/~   ~\\    || __/
                                         ~-----||====/~     |==================|       |/~~~~~
                                          (_(__/  ./     /                    \\_\\      \\.
                                                 (_(___/                         \\_____)_)
   "
}`;

export default {
  title: 'uikit/CodeEditorV2',
  component: CodeEditorV2,
  argTypes: {
    language: {
      description: 'highlighter language',
      defaultValue: 'json',
    },
    isSecret: {
      defaultValue: false,
    },
  },
} as Meta<typeof CodeEditorV2>;

const CodeEditorV2Example = ({ ...args }) => {
  const [code, setCode] = useState(args.code);
  return <CodeEditorV2 code={code} language={args.language} isSecret={args.isSecret} onChange={setCode} />;
};

export const CodeEditorV2Story: Story = {
  args: {
    language: 'json',
    code: jsonText,
    isSecret: false,
  },
  render: (args) => {
    return (
      <div style={{ height: '500px' }}>
        <CodeEditorV2Example {...args} />
      </div>
    );
  },
};
