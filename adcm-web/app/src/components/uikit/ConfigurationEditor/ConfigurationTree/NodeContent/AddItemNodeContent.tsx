import { useRef } from 'react';
import { Icon } from '@uikit';
import { ConfigurationNode } from '../../ConfigurationEditor.types';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';
import { textToDataTestValue } from '@utils/dataTestUtils.ts';

export interface AddItemNodeContentProps {
  node: ConfigurationNode;
  onClick: (node: ConfigurationNode, nodeRef: React.RefObject<HTMLElement>) => void;
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
      <Icon name="g1-add" size={16} /> {node.data.title}
    </div>
  );
};

export default AddItemNodeContent;
