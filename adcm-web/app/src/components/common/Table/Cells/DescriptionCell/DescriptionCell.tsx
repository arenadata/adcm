import { ConditionalWrapper, IconButton, TableCell, Tooltip } from '@uikit';
import s from './DescriptionCell.module.scss';
import { truncateString } from '@utils/stringUtils';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';

export interface DescriptionCellProps {
  description?: string;
  onEdit: () => void;
}

const DescriptionCell = ({ description = '', onEdit }: DescriptionCellProps) => {
  return (
    <TableCell className={s.descriptionCell}>
      <FlexGroup gap="10px">
        <ConditionalWrapper Component={Tooltip} isWrap={!!description} label={description} placement="top">
          <span>{truncateString(description, 20)}</span>
        </ConditionalWrapper>
        <IconButton icon="g1-edit" size={32} onClick={onEdit} />
      </FlexGroup>
    </TableCell>
  );
};

export default DescriptionCell;
