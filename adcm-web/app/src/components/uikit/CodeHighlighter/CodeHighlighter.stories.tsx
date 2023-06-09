import CodeHighlighter from './CodeHighlighter';
import { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof CodeHighlighter>;

const ansibleText = `PLAY [diamond:graphite:grafana] ************************************************

TASK [diamond : Stop Diamond service] ******************************************
Monday 14 March 2022  11:06:24 +0000 (0:00:00.077)       0:00:00.077 ********** 
fatal: [mon-mail-cnt-01]: UNREACHABLE! => changed=false 
  msg: 'Failed to connect to the host via ssh: ssh: connect to host 10.92.6.39 port 22: Operation timed out'
  unreachable: true
fatal: [secondary-ambari]: UNREACHABLE! => changed=false 
  msg: 'Failed to connect to the host via ssh: ssh: connect to host 10.92.3.5 port 22: Operation timed out'
  unreachable: true

PLAY RECAP *********************************************************************
mon-mail-cnt-01            : ok=0    changed=0    unreachable=1    failed=0    skipped=0    rescued=0    ignored=0   
secondary-ambari           : ok=0    changed=0    unreachable=1    failed=0    skipped=0    rescued=0    ignored=0   

Monday 14 March 2022  11:06:34 +0000 (0:00:10.039)       0:00:10.116 ********** 
=============================================================================== 
diamond : Stop Diamond service ----------------------------------------- 10.04s`;

export default {
  title: 'uikit/CodeHighlighter',
  component: CodeHighlighter,
  argTypes: {
    notCopy: {
      description: 'Remove copy button',
      defaultValue: false,
    },
    language: {
      description: 'highlighter language',
      defaultValue: 'bash',
    },
    CodeTagComponent: {
      table: {
        disable: true,
      },
    },
  },
} as Meta<typeof CodeHighlighter>;

export const CodeHighlighterExample: Story = {
  args: {
    language: 'bash',
    code: ansibleText,
  },
  render: (args) => {
    return <CodeHighlighter code={args.code} language={args.language} notCopy={args.notCopy} />;
  },
};
