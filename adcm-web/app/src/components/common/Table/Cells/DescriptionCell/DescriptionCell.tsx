import { ConditionalWrapper, IconButton, TableCell, Tooltip } from '@uikit';
import s from './DescriptionCell.module.scss';
import { truncateString } from '@utils/stringUtils';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import type { AdcmCluster } from '@models/adcm';
import { openClusterDescriptionChangeDialog } from '@store/adcm/clusters/clustersActionsSlice';
import { useDispatch } from '@hooks';

export interface DescriptionCellProps {
  cluster: AdcmCluster;
}

const DescriptionCell = ({ cluster }: DescriptionCellProps) => {
  const dispatch = useDispatch();

  const handleDescriptionChangeClick = (cluster: AdcmCluster) => {
    dispatch(openClusterDescriptionChangeDialog(cluster));
  };

  return (
    <TableCell className={s.descriptionCell}>
      <FlexGroup gap="10px">
        <ConditionalWrapper
          Component={Tooltip}
          isWrap={!!cluster.description}
          label={cluster.description}
          placement="top"
        >
          <span>{truncateString(cluster.description, 20)}</span>
        </ConditionalWrapper>
        <IconButton icon="g1-edit" size={32} onClick={() => handleDescriptionChangeClick(cluster)} />
      </FlexGroup>
    </TableCell>
  );
};

export default DescriptionCell;
