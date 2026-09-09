import React, { useCallback, useState } from 'react';
import cn from 'classnames';
import {
  autoUpdate,
  flip,
  FloatingPortal,
  offset,
  safePolygon,
  shift,
  useDismiss,
  useFloating,
  useHover,
  useInteractions,
  useRole,
} from '@floating-ui/react';
import s from './BulkOperationsMenu.module.scss';
import selectListStyles from '@uikit/Select/SingleSelect/SingleSelectList/SingleSelectList.module.scss';
import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';
import Tooltip from '@uikit/Tooltip/Tooltip';
import Icon from '@uikit/Icon/Icon';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import type { CommonHostAction } from '@pages/HostsPage/hostsBulkOperations.utils';

export interface BulkOperationsMenuItem {
  label: string;
  disabled?: boolean;
  title?: string;
  withDividerBefore?: boolean;
  onClick?: () => void;
  actions?: CommonHostAction[];
  onSelectAction?: (action: CommonHostAction) => void;
}

interface BulkOperationsMenuProps {
  items: BulkOperationsMenuItem[];
}

const tooltipPlacement = 'bottom-start' as const;
const submenuOffsetPx = 7;

const BulkOperationsMenu: React.FC<BulkOperationsMenuProps> = ({ items }) => {
  return (
    <ul className={cn(s.bulkOperationsMenu, 'scroll')}>
      {items.map((item) => (
        <React.Fragment key={item.label}>
          {item.withDividerBefore && <li className={s.bulkOperationsMenuDivider} aria-hidden="true" />}
          <BulkOperationsMenuItemRow item={item} />
        </React.Fragment>
      ))}
    </ul>
  );
};

interface BulkOperationsMenuItemRowProps {
  item: BulkOperationsMenuItem;
}

const BulkOperationsMenuItemRow: React.FC<BulkOperationsMenuItemRowProps> = ({ item }) => {
  if (item.actions !== undefined) {
    return <BulkOperationsSubmenuItemRow item={item} actions={item.actions} />;
  }

  return <BulkOperationsSimpleItemRow item={item} />;
};

interface BulkOperationsSimpleItemRowProps {
  item: BulkOperationsMenuItem;
}

const BulkOperationsSimpleItemRow: React.FC<BulkOperationsSimpleItemRowProps> = ({ item }) => {
  const itemClassName = cn(selectListStyles.singleSelectListItem, s.bulkOperationsMenuItem, {
    [selectListStyles.singleSelectListItem_disabled]: item.disabled,
  });

  const handleClick = () => {
    if (item.disabled) {
      return;
    }

    item.onClick?.();
  };

  return (
    <ConditionalWrapper Component={Tooltip} isWrap={!!item.title} label={item.title} placement={tooltipPlacement}>
      <li className={itemClassName} onClick={handleClick}>
        <span>{item.label}</span>
      </li>
    </ConditionalWrapper>
  );
};

interface BulkOperationsSubmenuItemRowProps {
  item: BulkOperationsMenuItem;
  actions: CommonHostAction[];
}

const BulkOperationsSubmenuItemRow: React.FC<BulkOperationsSubmenuItemRowProps> = ({ item, actions }) => {
  const [isSubmenuOpen, setIsSubmenuOpen] = useState(false);

  const hasAvailableActions = actions.length > 0;
  const isSubmenuInteractive = !item.disabled && hasAvailableActions;

  const { refs, floatingStyles, context } = useFloating({
    open: isSubmenuInteractive && isSubmenuOpen,
    onOpenChange: setIsSubmenuOpen,
    placement: 'right-start',
    middleware: [offset(submenuOffsetPx), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  const hover = useHover(context, {
    enabled: isSubmenuInteractive,
    handleClose: safePolygon({ buffer: 1 }),
  });
  const dismiss = useDismiss(context);
  const role = useRole(context, { role: 'menu' });
  const { getReferenceProps, getFloatingProps } = useInteractions([hover, dismiss, role]);

  const itemClassName = cn(selectListStyles.singleSelectListItem, s.bulkOperationsMenuItem, {
    [selectListStyles.singleSelectListItem_disabled]: item.disabled,
    [s.bulkOperationsMenuItem_active]: isSubmenuOpen,
  });

  const handleSelectAction = useCallback(
    (action: CommonHostAction) => {
      item.onSelectAction?.(action);
    },
    [item.onSelectAction],
  );

  return (
    <>
      <ConditionalWrapper
        Component={Tooltip}
        isWrap={!!item.title}
        label={item.title}
        placement={tooltipPlacement}
        className={s.bulkOperationsMenuItem__tooltip}
      >
        <li className={itemClassName} ref={refs.setReference} {...getReferenceProps()}>
          <span>{item.label}</span>
          <Icon name="chevron" size={10} className={s.bulkOperationsMenuItem__chevron} />
        </li>
      </ConditionalWrapper>
      {isSubmenuOpen && (
        <FloatingPortal>
          <PopoverPanelDefault
            ref={refs.setFloating}
            style={{
              ...floatingStyles,
              maxWidth: '100vw',
              zIndex: 'var(--z-index-popover)',
            }}
            {...getFloatingProps()}
          >
            <ul className={cn(s.bulkOperationsMenu, s.bulkOperationsMenu_submenu, 'scroll')}>
              {actions.map((action) => (
                <BulkOperationsSubmenuAction key={action.name} action={action} onSelect={handleSelectAction} />
              ))}
            </ul>
          </PopoverPanelDefault>
        </FloatingPortal>
      )}
    </>
  );
};

interface BulkOperationsSubmenuActionProps {
  action: CommonHostAction;
  onSelect: (action: CommonHostAction) => void;
}

const BulkOperationsSubmenuAction: React.FC<BulkOperationsSubmenuActionProps> = ({ action, onSelect }) => {
  const isDisabled = !!action.disabledReason;

  const actionClassName = cn(selectListStyles.singleSelectListItem, s.bulkOperationsMenuItem, {
    [selectListStyles.singleSelectListItem_disabled]: isDisabled,
  });

  const handleClick = () => {
    if (isDisabled) {
      return;
    }

    onSelect(action);
  };

  return (
    <ConditionalWrapper
      Component={Tooltip}
      isWrap={isDisabled}
      label={action.disabledReason}
      placement={tooltipPlacement}
    >
      <li className={actionClassName} onClick={handleClick}>
        <span>{action.displayName}</span>
      </li>
    </ConditionalWrapper>
  );
};

export default BulkOperationsMenu;
