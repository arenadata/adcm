import type React from 'react';
import { useCallback, useRef } from 'react';
import { Button, Popover, PopoverPanelDefault } from '@uikit';
import BulkOperationsMenu from './BulkOperationsMenu/BulkOperationsMenu';
import { useHostsBulkOperationsMenu } from './useHostsBulkOperationsMenu';
import cn from 'classnames';
import s from './HostsBulkOperationsButton.module.scss';

const HostsBulkOperationsButton: React.FC = () => {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const { isOpen, setIsOpen, isDisabled, menuItems } = useHostsBulkOperationsMenu();

  const handleToggleMenu = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, [setIsOpen]);

  return (
    <>
      <Button
        ref={triggerRef}
        variant="secondary"
        disabled={isDisabled}
        iconRight={{ name: 'chevron', size: 12 }}
        className={cn(s.bulkOperationsButton, { [s.bulkOperationsButton_open]: isOpen })}
        onClick={handleToggleMenu}
      >
        Bulk operations
      </Button>
      <Popover isOpen={isOpen} onOpenChange={setIsOpen} triggerRef={triggerRef} placement="bottom-end">
        <PopoverPanelDefault>
          <BulkOperationsMenu items={menuItems} />
        </PopoverPanelDefault>
      </Popover>
    </>
  );
};

export default HostsBulkOperationsButton;
