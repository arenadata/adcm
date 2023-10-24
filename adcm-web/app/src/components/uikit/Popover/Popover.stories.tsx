/* eslint-disable spellcheck/spell-checker */
import React, { useRef, useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import Popover, { PopoverProps } from './Popover';
import Button from '@uikit/Button/Button';
import Input from '@uikit/Input/Input';

type Story = StoryObj<typeof Popover>;
export default {
  title: 'uikit/Popover',
  component: Popover,
  argTypes: {
    children: {
      table: {
        disable: true,
      },
    },
    isOpen: {
      table: {
        disable: true,
      },
    },
    onOpenChange: {
      table: {
        disable: true,
      },
    },
    triggerRef: {
      table: {
        disable: true,
      },
    },
  },
} as Meta<typeof Popover>;

const EasyPopoverExample: React.FC<PopoverProps> = ({ dependencyWidth, placement, offset }) => {
  const [isOpen, setIsOpen] = useState(false);
  const localRef = useRef(null);

  const handleClick = () => {
    setIsOpen((prev) => !prev);
  };

  return (
    <div style={{ minHeight: 'calc(100vh - 2rem)', display: 'flex' }}>
      <Button ref={localRef} onClick={handleClick} style={{ margin: 'auto' }}>
        Click for show popover
      </Button>
      <Popover
        isOpen={isOpen}
        onOpenChange={setIsOpen}
        triggerRef={localRef}
        dependencyWidth={dependencyWidth}
        placement={placement}
        offset={offset}
      >
        <div style={{ background: 'green', color: '#000', fontSize: '30px', minHeight: '100px' }}>
          Show Popup content
        </div>
      </Popover>
    </div>
  );
};
export const EasyPopover: Story = {
  args: {
    placement: 'bottom',
    offset: 8,
    dependencyWidth: 'min-parent',
  },
  render: (args) => {
    return <EasyPopoverExample {...args} />;
  },
};

const PopoverInPopoverExample: React.FC = () => {
  const [isPrimaryOpen, setIsPrimaryOpen] = useState(false);
  const primaryRef = useRef(null);
  const handlePrimaryClick = () => {
    setIsPrimaryOpen((prev) => !prev);
  };

  const [isSecondaryOpen, setIsSecondaryOpen] = useState(false);
  const secondaryRef = useRef(null);

  const handleSecondaryClick = () => {
    setIsSecondaryOpen((prev) => !prev);
  };

  return (
    <div style={{ display: 'flex' }}>
      <Button ref={primaryRef} onClick={handlePrimaryClick} style={{ margin: 'auto' }}>
        Click for show Primary Popover
      </Button>
      <Popover isOpen={isPrimaryOpen} onOpenChange={setIsPrimaryOpen} triggerRef={primaryRef}>
        <div style={{ background: 'green', color: '#000', fontSize: '30px', minHeight: '200px', padding: '20px' }}>
          <div style={{ display: 'flex' }}>
            <Button ref={secondaryRef} onClick={handleSecondaryClick} style={{ margin: 'auto' }}>
              Click for show Secondary Popover
            </Button>
            <Popover isOpen={isSecondaryOpen} onOpenChange={setIsSecondaryOpen} triggerRef={secondaryRef}>
              <div style={{ background: 'red', color: 'blue', fontSize: '20px', minHeight: '100px', padding: '10px' }}>
                Show Popup content
                <Input />
              </div>
            </Popover>
          </div>
        </div>
      </Popover>
    </div>
  );
};

export const PopoverInPopover: Story = {
  render: () => {
    return <PopoverInPopoverExample />;
  },
};
