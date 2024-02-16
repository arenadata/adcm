import React, { useEffect } from 'react';
import {
  autoUpdate,
  flip,
  FloatingFocusManager,
  FloatingPortal,
  offset,
  shift,
  useDismiss,
  useFloating,
  useInteractions,
  useRole,
} from '@floating-ui/react';
import { getWidthStyles } from '@uikit/Popover/Popover.utils';
import { useForwardRef } from '@hooks';
import { ChildWithRef } from '@uikit/types/element.types';
import { PopoverOptions } from '@uikit/Popover/Popover.types';

export interface PopoverProps extends PopoverOptions {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  triggerRef: React.RefObject<HTMLElement>;
  children: ChildWithRef;
  initialFocus?: number | React.MutableRefObject<HTMLElement | null>;
}
const Popover: React.FC<PopoverProps> = ({
  isOpen,
  onOpenChange,
  children,
  triggerRef,
  placement = 'bottom-start',
  offset: offsetValue = 10,
  dependencyWidth,
  initialFocus,
}) => {
  const { refs, floatingStyles, context } = useFloating({
    placement,
    open: isOpen,
    onOpenChange,
    middleware: [offset(offsetValue), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  useEffect(() => {
    triggerRef.current && refs.setReference(triggerRef.current);
  }, [triggerRef, refs]);

  const dismiss = useDismiss(context);
  const role = useRole(context);

  const { getFloatingProps } = useInteractions([dismiss, role]);

  const popoverPanel = React.Children.only(children);
  const ref = useForwardRef(refs.setFloating, children.ref);
  const panelStyle = { ...(children.props.style ?? {}), maxWidth: '100vw', ...floatingStyles };
  if (dependencyWidth) {
    Object.entries(getWidthStyles(dependencyWidth, triggerRef)).forEach(([cssProperty, value]) => {
      panelStyle[cssProperty] = value;
    });
  }

  return (
    <FloatingPortal>
      {isOpen && (
        <FloatingFocusManager context={context} initialFocus={initialFocus}>
          {React.cloneElement(popoverPanel, { ref, ...children.props, style: panelStyle, ...getFloatingProps() })}
        </FloatingFocusManager>
      )}
    </FloatingPortal>
  );
};
export default Popover;
