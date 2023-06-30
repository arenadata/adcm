import React, { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import Select from '@uikit/Select/SingleSelect/Select/Select';
import SelectAction from '@uikit/Select/SingleSelect/SelectAction/SelectAction';
import Dialog from '@uikit/Dialog/Dialog';

type Story = StoryObj<typeof Select>;
export default {
  title: 'uikit/Select',
  argTypes: {
    isSearchable: {
      control: { type: 'boolean' },
    },
    noneLabel: {
      control: { type: 'text' },
    },
  },
  component: Select,
} as Meta<typeof Select>;

const options = [
  {
    value: 123,
    label: 'A 123',
  },
  {
    value: 234,
    label: 'A 234',
  },
  {
    value: 345,
    label: 'A 345',
  },
  {
    value: 456,
    label: 'A 456',
  },
  {
    value: 567,
    label: 'A 567',
  },
  {
    value: 678,
    label: 'A 678',
  },
  {
    value: 789,
    label: 'A 789',
  },
];

type SingleSelectExampleProps = {
  isSearchable?: boolean;
  noneLabel?: string;
};
const SingleSelectExample: React.FC<SingleSelectExampleProps> = ({ isSearchable, noneLabel }) => {
  const [value, setValue] = useState<number | null>(options[0].value);

  return (
    <div style={{ padding: 30, display: 'flex', alignItems: 'center' }}>
      <Select value={value} onChange={setValue} options={options} isSearchable={isSearchable} noneLabel={noneLabel} />
    </div>
  );
};

export const SingleSelect: Story = {
  args: {
    isSearchable: false,
    noneLabel: undefined,
  },
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  render: ({ isSearchable, noneLabel }) => {
    return <SingleSelectExample isSearchable={isSearchable} noneLabel={noneLabel} />;
  },
};

const actionsOptions = [
  {
    value: 'start',
    label: 'Start Action',
  },
  {
    value: 'stop',
    label: 'Stop Action',
  },
  {
    value: 'pause',
    label: 'Pause Action',
  },
];

const SingleSelectActionExample: React.FC = () => {
  const [isOpenStart, setIsOpenStart] = useState(false);
  const [isOpenStop, setIsOpenStop] = useState(false);
  const [isOpenPause, setIsOpenPause] = useState(false);

  const handleSelectActions = (val: string | null) => {
    setIsOpenStart(val === 'start');
    setIsOpenStop(val === 'stop');
    setIsOpenPause(val === 'pause');
  };

  return (
    <div style={{ padding: 30, display: 'flex', alignItems: 'center' }}>
      <SelectAction icon="g1-actions" size={34} value={null} onChange={handleSelectActions} options={actionsOptions} />
      <Dialog
        isOpen={isOpenStart}
        onOpenChange={setIsOpenStart}
        onAction={() => {
          setIsOpenStart(false);
        }}
      >
        Action &quot;Start&quot; about
      </Dialog>
      <Dialog
        isOpen={isOpenStop}
        onOpenChange={setIsOpenStop}
        onAction={() => {
          setIsOpenStop(false);
        }}
      >
        Action &quot;Stop&quot; about
      </Dialog>
      <Dialog
        isOpen={isOpenPause}
        onOpenChange={setIsOpenPause}
        onAction={() => {
          setIsOpenPause(false);
        }}
      >
        Action &quot;Pause&quot; about
      </Dialog>
    </div>
  );
};
export const SingleSelectAction: Story = {
  render: () => {
    return <SingleSelectActionExample />;
  },
};
