import { Button, DialogV2 } from '@uikit';
import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import type { DialogV2Props } from '@uikit/DialogV2/Dialog';

type Story = StoryObj<typeof DialogV2>;
export default {
  title: 'uikit/DialogV2',
  component: DialogV2,
  argTypes: {
    onOpenChange: {
      table: {
        disable: true,
      },
    },
    isPrimaryOpen: {
      table: {
        disable: true,
      },
    },
    dialogFooter: {
      table: {
        disable: true,
      },
    },
  },
} as Meta<typeof DialogV2>;

const EasyDialogV2Example: React.FC<DialogV2Props> = (props) => {
  const [isOpen, setIsOpen] = useState(false);
  const handleAction = () => {
    props.onAction?.();
    setIsOpen(false);
  };
  return (
    <>
      <Button onClick={() => setIsOpen((prev) => !prev)}>Click for open dialog</Button>
      {isOpen && (
        <DialogV2 {...props} onAction={handleAction}>
          <div>
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam commodo dui vel turpis mollis dignissim.
            Aliquam semper risus sollicitudin, consectetur risus aliquam, fringilla neque. Sed cursus elit eu sem
            bibendum euismod sit amet in erat. Sed id congue libero. Maecenas in commodo nisl, et eleifend lacus. Ut
            convallis eros eget justo sollicitudin pulvinar. Sed eu tellus quis erat auctor tincidunt sit amet eu augue.
            In fermentum egestas mauris vitae porttitor. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla
            facilisi. Sed odio nunc, feugiat vel finibus dapibus, molestie a ipsum. Aenean scelerisque eget ipsum eget
            luctus.
          </div>
        </DialogV2>
      )}
    </>
  );
};
export const EasyDialogV2: Story = {
  args: {
    title: 'Lorem ipsum',
    width: '584px',
  },
  render: (args) => {
    return <EasyDialogV2Example {...args} />;
  },
};

const DialogV2WithCancelConfirmationExample: React.FC<DialogV2Props> = (props) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleAction = () => {
    props.onAction?.();
    setIsOpen(false);
  };

  return (
    <>
      <Button onClick={() => setIsOpen((prev) => !prev)}>Click for open dialog</Button>
      {isOpen && (
        <DialogV2 {...props} onAction={handleAction}>
          <div>
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam commodo dui vel turpis mollis dignissim.
            Aliquam semper risus sollicitudin, consectetur risus aliquam, fringilla neque. Sed cursus elit eu sem
            bibendum euismod sit amet in erat. Sed id congue libero. Maecenas in commodo nisl, et eleifend lacus. Ut
            convallis eros eget justo sollicitudin pulvinar. Sed eu tellus quis erat auctor tincidunt sit amet eu augue.
            In fermentum egestas mauris vitae porttitor. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla
            facilisi. Sed odio nunc, feugiat vel finibus dapibus, molestie a ipsum. Aenean scelerisque eget ipsum eget
            luctus.
          </div>
        </DialogV2>
      )}
    </>
  );
};
export const DialogV2WithCancelConfirmation: Story = {
  args: {
    title: 'Lorem ipsum',
    width: '584px',
    isNeedConfirmationOnCancel: true,
  },
  render: (args) => {
    return <DialogV2WithCancelConfirmationExample {...args} />;
  },
};
