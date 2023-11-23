import React, { useMemo } from 'react';
import { AdcmDynamicAction } from '@models/adcm/dynamicAction';
import ActionMenu from '@uikit/ActionMenu/ActionMenu';
import IconButton from '@uikit/IconButton/IconButton';
import { ChildWithRef } from '@uikit/types/element.types';
import { IconProps } from '@uikit/Icon/Icon';
import { Button } from '@uikit';

interface DynamicActionsCommonProps {
  actions: AdcmDynamicAction[] | null;
  onSelectAction: (actionId: number) => void;
  children: ChildWithRef;
}

const DynamicActionsCommon: React.FC<DynamicActionsCommonProps> = ({ actions, children, onSelectAction }) => {
  const dynamicActionsOptions = useMemo(() => {
    return (actions ?? []).map(({ displayName, id, startImpossibleReason }) => ({
      label: displayName,
      value: id,
      disabled: startImpossibleReason !== null,
      title: startImpossibleReason,
    }));
  }, [actions]);

  const handleChange = (actionId: number | null) => {
    actionId && onSelectAction(actionId);
  };

  return (
    <ActionMenu placement="bottom-end" value={null} options={dynamicActionsOptions} onChange={handleChange}>
      {children}
    </ActionMenu>
  );
};

type DynamicActionsButtonProps = Omit<DynamicActionsCommonProps, 'children'> & {
  disabled?: boolean;
};

type DynamicActionsIconProps = Omit<DynamicActionsCommonProps, 'children'> & {
  size?: IconProps['size'];
  disabled?: boolean;
};

export const DynamicActionsIcon: React.FC<DynamicActionsIconProps> = ({ disabled, size = 32, ...props }) => {
  return (
    <DynamicActionsCommon {...props}>
      <IconButton icon="g1-actions" size={size} disabled={disabled} title="Action" />
    </DynamicActionsCommon>
  );
};

export const DynamicActionsButton: React.FC<DynamicActionsButtonProps> = ({ disabled, ...props }) => {
  return (
    <DynamicActionsCommon {...props}>
      <Button iconLeft="g1-actions" variant="secondary" disabled={disabled}>
        Actions
      </Button>
    </DynamicActionsCommon>
  );
};
