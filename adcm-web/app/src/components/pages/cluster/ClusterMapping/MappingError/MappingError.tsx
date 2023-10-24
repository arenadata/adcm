import { useState, useRef } from 'react';
import { Popover } from '@uikit';
import s from './MappingError.module.scss';

export interface MappingErrorProps {
  message: string;
}

const MappingError = ({ message }: MappingErrorProps) => {
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

  return (
    <>
      <span
        ref={triggerRef}
        className={s.mappingError__message}
        onMouseEnter={handleHover}
        onMouseLeave={handleMouseLeave}
      >
        {message}
      </span>
      <Popover
        isOpen={hasOverflowingChildren}
        onOpenChange={setHasOverflowingChildren}
        triggerRef={triggerRef}
        dependencyWidth="min-parent"
        offset={12}
      >
        <div className={s.mappingError__tooltip}>{message}</div>
      </Popover>
    </>
  );
};

export default MappingError;
