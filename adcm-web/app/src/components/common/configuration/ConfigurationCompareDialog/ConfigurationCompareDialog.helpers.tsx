import type { AdcmConfigShortView } from '@models/adcm';
import type { DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import SingleSelectListItem from '@uikit/Select/SingleSelect/SingleSelectList/SingleSelectListItem/SingleSelectListItem';
import { dateToString } from '@utils/date/dateConvertUtils';
import s from './ConfigurationCompareDialog.module.scss';

export const prepareDate = (value: string) => {
  return dateToString(new Date(value), { toUtc: true });
};

export const renderConfigContent = (configId: number | null, configVersions: AdcmConfigShortView[]) => {
  if (configId === 0) {
    return <>now - Draft Configuration</>;
  }

  const config = configVersions.find((c) => c.id === configId);
  if (!config) return <></>;

  const date = prepareDate(config.creationTime);
  const description = config.description || String(config.id);
  const createdBy = config.createdBy;

  return (
    <>
      <span>
        {date} - {description}
      </span>
      <span className={s.configurationCompareDialog__createdByField}>{createdBy}</span>
    </>
  );
};

export const createConfigSelectItem = (configVersions: AdcmConfigShortView[]) => {
  return (props: DefaultSelectListItemProps<number>) => {
    const { option, onSelect } = props;

    const handleClick = () => {
      onSelect?.(option.value);
    };

    return (
      <SingleSelectListItem {...props} option={option} onSelect={onSelect}>
        <span onClick={handleClick}>{renderConfigContent(option.value, configVersions)}</span>
      </SingleSelectListItem>
    );
  };
};
