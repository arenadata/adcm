import type { AdcmUpgradeShort } from '@models/adcm';
import { Icon, Tooltip } from '@uikit';
import type { DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import SingleSelectListItem from '@uikit/Select/SingleSelect/SingleSelectList/SingleSelectListItem/SingleSelectListItem';
import BundleVersionTooltipContent from './BundleVersionTooltipContent/BundleVersionTooltipContent';
import s from './BundleVersionSelectItem.module.scss';
import cn from 'classnames';

interface BundleVersionSelectItemProps extends DefaultSelectListItemProps<number> {
  version: AdcmUpgradeShort;
}

const BundleVersionSelectItem = (props: BundleVersionSelectItemProps) => {
  const { label, value } = props.option;

  const handleChange = () => {
    props.onSelect?.(value);
  };

  const itemClassName = cn(s.bundleVersionSelectItem, {
    [s.bundleVersionSelectItem_selected]: props.isSelected,
  });

  return (
    <SingleSelectListItem {...props} className={itemClassName}>
      <div className={s.bundleVersionSelectItem__row} onClick={handleChange}>
        <span>{label}</span>
        <Tooltip label={<BundleVersionTooltipContent version={props.version} />} placement="top-start">
          <Icon size={24} name="g1-info" className={s.bundleVersionSelectItem__icon} />
        </Tooltip>
      </div>
    </SingleSelectListItem>
  );
};

export default BundleVersionSelectItem;
