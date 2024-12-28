import type { DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import { ConditionalWrapper, Tooltip } from '@uikit';

const AboutAdcm = <T,>({ className, onSelect, option: { title, label } }: DefaultSelectListItemProps<T>) => {
  return (
    <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} placement="bottom-start">
      <li className={className} onClick={onSelect}>
        {label}
      </li>
    </ConditionalWrapper>
  );
};

export default AboutAdcm;
