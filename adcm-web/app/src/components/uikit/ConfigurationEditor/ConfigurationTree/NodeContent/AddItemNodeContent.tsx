import { useRef } from 'react';
import type { ConfigurationNodeView } from '../../ConfigurationEditor.types';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';
import { textToDataTestValue } from '@utils/dataTestUtils';
import Icon from '@uikit/Icon/Icon';

export interface AddItemNodeContentProps {
  node: ConfigurationNodeView;
  onClick: (node: ConfigurationNodeView, nodeRef: React.RefObject<HTMLElement>) => void;
  dataTest?: string;
}

const AddItemNodeContent = ({ node, onClick, dataTest }: AddItemNodeContentProps) => {
  const ref = useRef(null);

  const handleClick = () => {
    onClick(node, ref);
  };

  return (
    <div
      ref={ref}
      className={cn(s.nodeContent, s.addArrayItemNodeContent)}
      data-test={dataTest || textToDataTestValue(node.data.title)}
      onClick={handleClick}
    >
      <div className={cn(s.nodeContent__title, s.addArrayItemNodeContent__content)}>
        <Icon name="g3-add" size={14} /> {node.data.title}
      </div>
    </div>
  );
};

export default AddItemNodeContent;
