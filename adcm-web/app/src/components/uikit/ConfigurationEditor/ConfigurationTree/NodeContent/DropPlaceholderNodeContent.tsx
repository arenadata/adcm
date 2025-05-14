import { useRef } from 'react';
import type { ConfigurationNodeView } from '../../ConfigurationEditor.types';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';

export interface DropPlaceholderNodeContentProps {
  node: ConfigurationNodeView;
  onDrop: (node: ConfigurationNodeView, nodeRef: React.RefObject<HTMLElement>) => void;
  dataTest?: string;
}

const DropPlaceholderNodeContent = ({ node, onDrop, dataTest }: DropPlaceholderNodeContentProps) => {
  const ref = useRef(null);

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.stopPropagation();
    event.preventDefault();
  };

  const handleDrop = () => {
    onDrop(node, ref);
  };

  return (
    <div
      ref={ref}
      className={cn(s.nodeContent, s.dropPlaceholderContent)}
      data-test={dataTest}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div>&nbsp;</div>
    </div>
  );
};

export default DropPlaceholderNodeContent;
