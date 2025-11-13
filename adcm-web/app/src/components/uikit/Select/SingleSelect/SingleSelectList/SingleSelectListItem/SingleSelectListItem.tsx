import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';
import type { DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import Tooltip from '@uikit/Tooltip/Tooltip';

interface SingleSelectListItemProps<T> extends DefaultSelectListItemProps<T>, React.PropsWithChildren {}

const SingleSelectListItem = <T,>({ onSelect, option, className, children }: SingleSelectListItemProps<T>) => {
  const { disabled, title, value } = option;

  const handleClick = () => {
    if (disabled) return;
    onSelect?.(value);
  };

  return (
    <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} placement="bottom-start">
      <li className={className} onClick={handleClick}>
        {children}
      </li>
    </ConditionalWrapper>
  );
};

export default SingleSelectListItem;
