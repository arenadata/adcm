/* eslint-disable spellcheck/spell-checker */
import CodeHighlighter from './CodeHighlighter';
import type { StoryFn, Meta } from '@storybook/react';
import { CodeHighlighterContextProvider } from './context/CodeHighlighterContextProvider';

export default {
  title: 'uikit/CodeHighlighter',
  component: CodeHighlighter,
  argTypes: {
    isNotCopy: {
      description: 'Remove copy button',
      defaultValue: false,
    },
    language: {
      description: 'Language',
      defaultValue: 'sql',
      options: ['sql', 'bash'],
      control: { type: 'radio' },
    },
    CodeTagComponent: {
      table: {
        disable: true,
      },
    },
  },
} as Meta<typeof CodeHighlighter>;

const Template: StoryFn<typeof CodeHighlighter> = (args) => {
  return (
    <CodeHighlighterContextProvider>
      <div style={{ height: '500px', maxWidth: '1100px' }}>
        <CodeHighlighter code={args.code} language={args.language} isNotCopy={args.isNotCopy} />
      </div>
    </CodeHighlighterContextProvider>
  );
};

export const CodeHighlighterElement = Template.bind({});
CodeHighlighterElement.args = {
  isNotCopy: false,
  code: `select count(*), pg_sleep(20)
from dev1 t1, dev1 t2 where t1.id is not null
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit. Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.Lorem ipsum dolor sit amet, consectetur adipisicing elit. Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.Lorem ipsum dolor sit amet, consectetur adipisicing elit. Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.
-- Lorem ipsum dolor sit amet, consectetur adipisicing elit.
-- Dolores, quis quos. Ad alias commodi culpa eaque fugit ipsa numquam sequi.`,
  language: 'sql',
};

const original = {
  name: 'Adeel Solangi',
  language: 'Sindhi',
  id: 'V59OF92YF627HFY0',
  bio: 'Donec lobortis eleifend condimentum. Cras dictum dolor lacinia lectus vehicula rutrum. Maecenas quis nisi nunc. Nam tristique feugiat est vitae mollis. Maecenas quis nisi nunc.',
  version: 6.1,
};
const repeatedArray = Array(10000).fill(original);
const items = repeatedArray.map((obj) => JSON.stringify(obj));
const jsonString = `[\n${items.join(',\n')}\n]`;

export const CodeHighlighterElementBigJSON = Template.bind({});
CodeHighlighterElementBigJSON.args = {
  isNotCopy: false,
  code: jsonString,
  language: 'json',
};
