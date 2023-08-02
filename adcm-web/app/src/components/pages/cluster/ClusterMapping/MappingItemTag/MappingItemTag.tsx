import { Tag, IconButton } from '@uikit';

export interface MappingItemTagProps {
  id: number;
  label: string;
  onDeleteClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
}

const MappingItemTag = ({ id, label, onDeleteClick }: MappingItemTagProps) => (
  <Tag
    endAdornment={
      <IconButton
        //
        data-id={id}
        icon="g1-remove"
        variant="secondary"
        size={20}
        onClick={onDeleteClick}
        title="Remove"
      />
    }
  >
    {label}
  </Tag>
);

export default MappingItemTag;
