/* eslint-disable spellcheck/spell-checker */
import CodeHighlighter from './CodeHighlighter';
import type { StoryFn, Meta } from '@storybook/react';

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
    <div style={{ height: '500px', maxWidth: '1100px' }}>
      <CodeHighlighter code={args.code} language={args.language} isNotCopy={args.isNotCopy} />
    </div>
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
