import React, { CSSProperties } from 'react';
import { ModalOptions } from './Modal.types';
import {
  FloatingFocusManager,
  FloatingOverlay,
  FloatingPortal,
  useDismiss,
  useFloating,
  useInteractions,
  useRole,
} from '@floating-ui/react';
import s from './Modal.module.scss';
import cn from 'classnames';

interface ModalProps extends ModalOptions {
  children: React.ReactNode;
  className?: string;
  style?: CSSProperties;
  dataTest?: string;
}

const Modal: React.FC<ModalProps> = ({
  isOpen,
  onOpenChange,
  isDismissDisabled = false,
  className,
  style,
  children,
  dataTest = 'modal-container',
}) => {
  const { refs, context } = useFloating({
    open: isOpen,
    onOpenChange: onOpenChange,
  });

  const role = useRole(context);
  const dismiss = useDismiss(context, { enabled: !isDismissDisabled });

  const { getFloatingProps } = useInteractions([role, dismiss]);

  return (
    <FloatingPortal>
      {isOpen && (
        <FloatingOverlay className={s.modalOverlay} lockScroll>
          <FloatingFocusManager context={context}>
            <div
              ref={refs.setFloating}
              {...getFloatingProps()}
              className={cn(s.modal, className)}
              style={style}
              data-test={dataTest}
            >
              {children}
            </div>
          </FloatingFocusManager>
        </FloatingOverlay>
      )}
    </FloatingPortal>
  );
};
export default Modal;
