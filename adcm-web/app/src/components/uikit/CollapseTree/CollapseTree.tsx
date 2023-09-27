import React, { ReactNode, useState } from 'react';
import s from './CollapseTree.module.scss';
import Collapse from '@uikit/Collapse/Collapse';
import { getValueByPath } from '@utils/objectUtils';
import cn from 'classnames';

interface CollapseTreeProps<T extends object> {
  renderNode: (model: T, isExpanded: boolean) => ReactNode;
  childFieldName: keyof T;
  uniqueFieldName: string;
  getNodeClassName?: (model: T) => string;
  model: T;
}
const CollapseTree = <T extends object>({
  renderNode,
  childFieldName,
  uniqueFieldName,
  model,
  getNodeClassName,
}: CollapseTreeProps<T>) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const childrenModels = model[childFieldName] as T[];
  const hasChildren = childrenModels?.length > 0;

  const toggleCollapseNode = () => {
    if (hasChildren) {
      setIsExpanded((prev) => !prev);
    }
  };

  return (
    <div className={cn(s.collapseTreeNode, getNodeClassName?.(model))}>
      <div
        className={cn(s.collapseTreeNode__trigger, { [s.collapseTreeNode__trigger_enabled]: hasChildren })}
        onClick={toggleCollapseNode}
      >
        {renderNode(model, isExpanded)}
      </div>
      {hasChildren && (
        <div className={s.collapseTreeNode__children}>
          <Collapse isExpanded={isExpanded}>
            {childrenModels.map((childModel) => (
              <CollapseTree
                renderNode={renderNode}
                childFieldName={childFieldName}
                uniqueFieldName={uniqueFieldName}
                model={childModel}
                getNodeClassName={getNodeClassName}
                key={getValueByPath(childModel, uniqueFieldName)?.toString()}
              />
            ))}
          </Collapse>
        </div>
      )}
    </div>
  );
};
export default CollapseTree;
