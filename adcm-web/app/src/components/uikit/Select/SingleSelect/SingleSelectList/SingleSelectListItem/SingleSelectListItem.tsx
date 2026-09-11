import Tooltip from '@uikit/Tooltip/Tooltip';
import type { DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import Icon from '@uikit/Icon/Icon';

interface SingleSelectListItemProps<T> extends DefaultSelectListItemProps<T>, React.PropsWithChildren {}

const SingleSelectListItem = <T,>({ onSelect, option, className, children }: SingleSelectListItemProps<T>) => {
  const { disabled, title, value } = option;

  const handleClick = () => {
    if (disabled) return;
    onSelect?.(value);
  };

  return (
    <li className={className} onClick={handleClick}>
      <FlexGroup gap="8px">
        {children}

        {Boolean(title) && (
          <Tooltip label={title}>
            <Icon size={16} name="g2-information" />
          </Tooltip>
        )}
      </FlexGroup>
    </li>
  );
};

export default SingleSelectListItem;
