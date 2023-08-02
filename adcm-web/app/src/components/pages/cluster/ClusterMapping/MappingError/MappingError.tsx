import { useState, useRef } from 'react';
import { Popover } from '@uikit';
import s from './MappingError.module.scss';
import cn from 'classnames';

export interface MappingErrorProps {
  message: string;
  variant: 'error' | 'warning';
}

const MappingError = ({ message, variant }: MappingErrorProps) => {
  const [hasOverflowingChildren, setHasOverflowingChildren] = useState(false);
  const triggerRef = useRef(null);

  const handleHover = (e: React.MouseEvent<HTMLSpanElement>) => {
    const el = e.target as Element;

    if (!hasOverflowingChildren && el.scrollWidth > el.clientWidth) {
      setHasOverflowingChildren(true);
    } else {
      setHasOverflowingChildren(false);
    }
  };

  const handleMouseLeave = () => {
    setHasOverflowingChildren(false);
  };

  const tooltipClassName = cn(s.mappingError__tooltip, s[`mappingError__tooltip_${variant}`]);
  const messageClassName = cn(s.mappingError__message, s[`mappingError__message_${variant}`]);

  return (
    <>
      <span ref={triggerRef} className={messageClassName} onMouseEnter={handleHover} onMouseLeave={handleMouseLeave}>
        {message}
      </span>
      <Popover
        isOpen={hasOverflowingChildren}
        onOpenChange={setHasOverflowingChildren}
        triggerRef={triggerRef}
        dependencyWidth="min-parent"
        offset={12}
      >
        <div className={tooltipClassName}>{message}</div>
      </Popover>
    </>
  );
};

export default MappingError;
