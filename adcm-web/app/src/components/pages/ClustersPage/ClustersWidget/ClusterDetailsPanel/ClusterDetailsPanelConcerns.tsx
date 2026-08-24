import type React from 'react';
import { memo, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import cn from 'classnames';
import { IconButton, TabButton, TabsBlock, VirtualList } from '@uikit';
import type { AdcmConcerns } from '@models/adcm';
import { useDispatch } from '@hooks';
import { deleteClusterConcern } from '@store/adcm/concerns/concernsActionSlice';
import { getConcernLinkObjectPathsDataArray } from '@utils/concernUtils';
import s from './ClusterDetailsPanel.module.scss';

export interface ClusterDetailsPanelConcernsProps {
  concerns: AdcmConcerns[];
  className?: string;
  listClassName?: string;
  headerSlot?: React.ReactNode;
}

type ConcernListData = ReturnType<typeof getConcernLinkObjectPathsDataArray>[number];

type ConcernListItemProps = {
  concern: ConcernListData;
  index: number;
  isBlocking: boolean;
  onRemove: (concernId: number) => void;
};

const CONCERN_ITEM_ESTIMATE_SIZE = 52;

const ConcernListItem = memo(({ concern, index, isBlocking, onRemove }: ConcernListItemProps) => (
  <div
    className={cn(s.clusterDetailsPanel__concernItem, {
      [s.clusterDetailsPanel__concernItem_alt]: index % 2 === 0,
    })}
  >
    <span
      className={cn(s.clusterDetailsPanel__concernDot, {
        [s.clusterDetailsPanel__concernDot_blocking]: isBlocking,
        [s.clusterDetailsPanel__concernDot_nonBlocking]: !isBlocking,
      })}
    />
    <span className={s.clusterDetailsPanel__concernText}>
      {concern.concernData.map((part, partIndex) =>
        part.path ? (
          <Link key={`${concern.concernId}-${partIndex}`} to={part.path} className="text-link">
            {part.text}
          </Link>
        ) : (
          <span key={`${concern.concernId}-${partIndex}`}>{part.text}</span>
        ),
      )}
    </span>
    {concern.isDeletable && (
      <IconButton
        icon="g2-close"
        size={18}
        variant="secondary"
        className={s.clusterDetailsPanel__concernRemove}
        onClick={() => onRemove(concern.concernId)}
      />
    )}
  </div>
));

ConcernListItem.displayName = 'ConcernListItem';

const ClusterDetailsPanelConcerns: React.FC<ClusterDetailsPanelConcernsProps> = ({
  concerns,
  className,
  listClassName,
  headerSlot,
}) => {
  const dispatch = useDispatch();
  const concernsData = useMemo(() => getConcernLinkObjectPathsDataArray(concerns), [concerns]);
  const concernsById = useMemo(() => new Map(concerns.map((concern) => [concern.id, concern])), [concerns]);

  const handleRemove = useCallback(
    (concernId: number) => {
      dispatch(deleteClusterConcern(concernId));
    },
    [dispatch],
  );

  const renderItem = useCallback(
    (concern: ConcernListData, index: number) => (
      <ConcernListItem
        concern={concern}
        index={index}
        isBlocking={concernsById.get(concern.concernId)?.isBlocking ?? false}
        onRemove={handleRemove}
      />
    ),
    [concernsById, handleRemove],
  );

  return (
    <div className={cn(s.clusterDetailsPanel__card, className)}>
      {headerSlot ?? (
        <TabsBlock variant="secondary" className={s.clusterDetailsPanel__tabs}>
          <TabButton isActive>
            Concerns <span className={s.clusterDetailsPanel__tabCount}>{concerns.length}</span>
          </TabButton>
        </TabsBlock>
      )}

      <VirtualList
        items={concernsData}
        className={cn(s.clusterDetailsPanel__concernsList, listClassName)}
        getItemKey={(concern) => concern.concernId}
        estimateSize={CONCERN_ITEM_ESTIMATE_SIZE}
        emptyContent={<div className={s.clusterDetailsPanel__concernsEmpty}>No concerns</div>}
        renderItem={renderItem}
      />
    </div>
  );
};

export default ClusterDetailsPanelConcerns;
