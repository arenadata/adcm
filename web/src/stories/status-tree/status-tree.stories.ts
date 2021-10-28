import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTreeModule } from '@angular/material/tree';

import { Folding, StatusTreeComponent } from '../../app/components/status-tree/status-tree.component';
import { StatusTree } from '../../app/models/status-tree';

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
        status: 16,
      },
      children: [
        {
          subject: {
            name: 'Hosts',
            status: 16,
          },
          children: [
            {
              subject: {
                name: 'adb-spark-m.ru-central1.internal',
                status: 0,
              }
            },
            {
              subject: {
                name: 'adb-spark-seg1.ru-central1.internal',
                status: 1,
              }
            },
            {
              subject: {
                name: 'adb-spark-seg2.ru-central1.internal',
                status: 1,
              }
            }
          ]
        },
        {
          subject: {
            name: 'Services',
            status: 1,
          },
          children: [
            {
              subject: {
                name: 'Chrony',
                status: 0,
              },
              children: [
                {
                  subject: {
                    name: 'NTP Master',
                    status: 0,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-m.ru-central1.internal',
                        status: 0,
                      }
                    }
                  ]
                },
                {
                  subject: {
                    name: 'NTP Slave',
                    status: 0,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-seg1.ru-central1.internal',
                        status: 0,
                      }
                    },
                    {
                      subject: {
                        name: 'adb-spark-seg2.ru-central1.internal',
                        status: 0,
                      }
                    }
                  ]
                }

              ]
            },
            {
              subject: {
                name: 'ADB',
                status: 1,
              },
              children: [
                {
                  subject: {
                    name: 'ADB Master',
                    status: 0,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-m.ru-central1.internal',
                        status: 0,
                      }
                    }
                  ]
                },
                {
                  subject: {
                    name: 'ADB Segment',
                    status: 1,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-seg1.ru-central1.internal',
                        status: 0,
                      }
                    },
                    {
                      subject: {
                        name: 'adb-spark-seg2.ru-central1.internal',
                        status: 1,
                      }
                    }
                  ]
                }
              ]
            },
            {
              subject: {
                name: 'PXF',
                status: 0,
              },
              children: [
                {
                  subject: {
                    name: 'PXF',
                    status: 0,
                  },
                  children: [
                    {
                      subject: {
                        name: 'adb-spark-seg1.ru-central1.internal',
                        status: 0,
                      }
                    },
                    {
                      subject: {
                        name: 'adb-spark-seg2.ru-central1.internal',
                        status: 0,
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
