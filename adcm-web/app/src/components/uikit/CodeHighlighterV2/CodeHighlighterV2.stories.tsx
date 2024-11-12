/* eslint-disable spellcheck/spell-checker */
import CodeHighlighterV2 from './CodeHighlighterV2';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof CodeHighlighterV2>;

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
diamond : Stop Diamond service ----------------------------------------- 10.04s

PLAY RECAP *********************************************************************
mon-mail-cnt-01            : ok=0    changed=0    unreachable=1    failed=0    skipped=0    rescued=0    ignored=0
secondary-ambari           : ok=0    changed=0    unreachable=1    failed=0    skipped=0    rescued=0    ignored=0

Monday 14 March 2022  11:06:34 +0000 (0:00:10.039)       0:00:10.116 **********
======================================Long====String==================================================================================================================================================================================================================================================================================
======================================Long====String==================================================================================================================================================================================================================================================================================
diamond : Stop Diamond service ----------------------------------------- 10.04s

PLAY RECAP *********************************************************************
mon-mail-cnt-01            : ok=0    changed=0    unreachable=1    failed=0    skipped=0    rescued=0    ignored=0
secondary-ambari           : ok=0    changed=0    unreachable=1    failed=0    skipped=0    rescued=0    ignored=0

Monday 14 March 2022  11:06:34 +0000 (0:00:10.039)       0:00:10.116 **********
===============================================================================
diamond : Stop Diamond service ----------------------------------------- 10.04s

                       .-.
                      |_:_|
                     /(_Y_)\\
.                   ( \\/M\\/ )
 '.               _.'-/'-'\\-'._
   ':           _/.--'[[[[]'--.\\_
     ':        /_'  : |::"| :  '.\\
       ':     //   ./ |oUU| \\.'  :\\
         ':  _:'..' \\_|___|_/ :   :|
           ':.  .'  |_[___]_|  :.':\\
            [::\\ |  :  | |  :   ; : \\
             '-'   \\/'.| |.' \\  .;.' |
             |\\_    \\  '-'   :       |
             |  \\    \\ .:    :   |   |
             |   \\    | '.   :    \\  |
             /       \\   :. .;       |
            /     |   |  :__/     :  \\\\
           |  |   |    \\:   | \\   |   ||
          /    \\  : :  |:   /  |__|   /|
          |     : : :_/_|  /'._\\  '--|_\\
          /___.-/_|-'   \\  \\
                         '-'
`;

export default {
  title: 'uikit/CodeHighlighterV2',
  component: CodeHighlighterV2,
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
} as Meta<typeof CodeHighlighterV2>;

export const CodeHighlighterV2Example: Story = {
  args: {
    lang: 'bash',
    code: ansibleText,
  },
  render: (args) => {
    return (
      <div style={{ height: '500px', maxWidth: '1100px' }}>
        <CodeHighlighterV2 code={args.code} lang={args.lang} isNotCopy={args.isNotCopy} />
      </div>
    );
  },
};
