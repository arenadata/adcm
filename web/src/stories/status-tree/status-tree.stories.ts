import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTreeModule } from '@angular/material/tree';

import { Folding, StatusTreeComponent } from '../../app/components/status-tree/status-tree.component';
import { StatusTree, SubjectStatus } from '../../app/models/status-tree';

export default {
  title: 'ADCM/Status Tree',
  decorators: [
    moduleMetadata({
      declarations: [
        StatusTreeComponent,
      ],
      imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
        MatTreeModule,
      ],
    }),
  ],
  component: StatusTreeComponent,
  argTypes: {
    tree: {
      control: { type: 'object' }
    },
    folding: {
      options: ['Collapse all', 'Expand all'],
      mapping: { 'Collapse all': Folding.Collapsed, 'Expand all': Folding.Expanded },
      control: {
        type: 'select'
      }
    }
  },
  parameters: {
    docs: {
      page: null
    }
  },
} as Meta;

const Template: Story = args => ({
  props: {
    ...args,
  },
});

export const RegularTree = Template.bind({});
RegularTree.args = {
  folding: Folding.Expanded,
  tree: [
    {
      subject: {
        name: 'ADB Spark',
        status: SubjectStatus.Fail,
      },
      children: [
        {
          subject: {
            name: 'Hosts',
            status: SubjectStatus.Fail,
          },
          children: [
            {
              subject: {
                name: 'adb-spark-m.ru-central1.internal',
                status: SubjectStatus.Success,
              }
            },
            {
              subject: {
                name: 'adb-spark-seg1.ru-central1.internal',
                status: SubjectStatus.Fail,
              }
            },
            {
              subject: {
                name: 'adb-spark-seg2.ru-central1.internal',
                status: SubjectStatus.Fail,
              }
            }
          ]
        },
        {
          subject: {
            name: 'Services',
            status: SubjectStatus.Fail,
          },
          children: [
            {
              subject: {
                name: 'Chrony',
                status: SubjectStatus.Success,
              },
              children: [
                {
                  subject: {
                    name: 'NTP Master',
                    status: SubjectStatus.Success,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-m.ru-central1.internal',
                        status: SubjectStatus.Success,
                      }
                    }
                  ]
                },
                {
                  subject: {
                    name: 'NTP Slave',
                    status: SubjectStatus.Success,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-seg1.ru-central1.internal',
                        status: SubjectStatus.Success,
                      }
                    },
                    {
                      subject: {
                        name: 'adb-spark-seg2.ru-central1.internal',
                        status: SubjectStatus.Success,
                      }
                    }
                  ]
                }

              ]
            },
            {
              subject: {
                name: 'ADB',
                status: SubjectStatus.Fail,
              },
              children: [
                {
                  subject: {
                    name: 'ADB Master',
                    status: SubjectStatus.Success,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-m.ru-central1.internal',
                        status: SubjectStatus.Success,
                      }
                    }
                  ]
                },
                {
                  subject: {
                    name: 'ADB Segment',
                    status: SubjectStatus.Fail,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-seg1.ru-central1.internal',
                        status: SubjectStatus.Success,
                      }
                    },
                    {
                      subject: {
                        name: 'adb-spark-seg2.ru-central1.internal',
                        status: SubjectStatus.Fail,
                      }
                    }
                  ]
                }
              ]
            },
            {
              subject: {
                name: 'PXF',
                status: SubjectStatus.Success,
              },
              children: [
                {
                  subject: {
                    name: 'PXF',
                    status: SubjectStatus.Success,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-seg1.ru-central1.internal',
                        status: SubjectStatus.Success,
                      }
                    },
                    {
                      subject: {
                        name: 'adb-spark-seg2.ru-central1.internal',
                        status: SubjectStatus.Success,
                      }
                    }
                  ]
                }

              ]
            },
          ]
        },
      ]
    }
  ] as StatusTree[],
} ;
