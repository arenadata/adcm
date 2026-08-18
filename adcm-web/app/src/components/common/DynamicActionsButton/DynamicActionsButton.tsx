import type React from 'react';
import { useMemo } from 'react';
import type { AdcmDynamicAction } from '@models/adcm/dynamicAction';
import ActionMenu from '@uikit/ActionMenu/ActionMenu';
import IconButton from '@uikit/IconButton/IconButton';
import type { ChildWithRef } from '@uikit/types/element.types';
import type { IconProps } from '@uikit/Icon/Icon';
import type { IconsNames } from '@uikit/Icon/sprite';
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

interface PrepareViewInfo {
  disabled?: boolean;
  actions: AdcmDynamicAction[] | null;
}

const prepareViewInfo = ({ disabled, actions }: PrepareViewInfo) => {
  const isNoActions = !actions?.length;
  const reasons = (actions ?? []).map((a) => a.startImpossibleReason).filter((r) => !!r);

  const allHaveSameReason =
    !isNoActions && reasons.length === actions!.length && reasons.every((r) => r === reasons[0]);

  const commonReason = allHaveSameReason ? reasons[0] : null;

  const isDisabled = disabled || isNoActions || allHaveSameReason;
  const isLocked = disabled || allHaveSameReason;

  const title = disabled ? 'Actions are blocked' : isNoActions ? 'No Actions available' : (commonReason ?? 'Actions');

  const iconName: IconsNames = isLocked ? 'g1-actions-disabled' : 'g1-actions';

  return {
    isDisabled,
    title,
    iconName,
  };
};

export const DynamicActionsIcon: React.FC<DynamicActionsIconProps> = ({ disabled, size = 32, actions, ...props }) => {
  const { isDisabled, iconName, title } = prepareViewInfo({ disabled, actions });

  return (
    <DynamicActionsCommon {...props} actions={actions}>
      <IconButton
        //
        icon={iconName}
        size={size}
        disabled={isDisabled}
        title={title}
      />
    </DynamicActionsCommon>
  );
};

export const DynamicActionsButton: React.FC<DynamicActionsButtonProps> = ({ disabled, actions, ...props }) => {
  const { isDisabled, iconName, title } = prepareViewInfo({ disabled, actions });

  return (
    <DynamicActionsCommon {...props} actions={actions}>
      <Button
        //
        iconLeft={iconName}
        variant="secondary"
        disabled={isDisabled}
        title={title}
      >
        Actions
      </Button>
    </DynamicActionsCommon>
  );
};
