import { Icon, Tag, Tooltip } from '@uikit';
import s from './AccessManagerPoliciesTableExpandedContent.module.scss';
import type { AdcmPolicyObject } from '@models/adcm';

interface PolicyObjectTagProps {
  object: AdcmPolicyObject;
}

const getParentClusterName = (object: AdcmPolicyObject) => {
  if (object.type !== 'service') return null;

  return object.objects?.find((parent) => parent.type === 'cluster')?.name ?? null;
};

const PolicyObjectTag = ({ object }: PolicyObjectTagProps) => {
  const parentClusterName = getParentClusterName(object);

  const parentInfo = parentClusterName ? (
    <Tooltip label={`Parent: ${parentClusterName}`} placement="bottom-start">
      <Icon name="g1-info" size={16} className={s.content__parentIcon} />
    </Tooltip>
  ) : null;

  return <Tag endAdornment={parentInfo}>{object.displayName}</Tag>;
};

export default PolicyObjectTag;
