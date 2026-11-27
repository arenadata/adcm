import { Tags } from '@uikit';
import PolicyObjectTag from './PolicyObjectTag';
import s from './AccessManagerPoliciesTableExpandedContent.module.scss';
import type { AdcmPolicyObject } from '@models/adcm';

interface PolicyObjectsGroupProps {
  type: string;
  objects: AdcmPolicyObject[];
}

const PolicyObjectsGroup = ({ type, objects }: PolicyObjectsGroupProps) => (
  <div>
    <div className={s.content__title}>{type}</div>
    <Tags className={s.content__tags}>
      {objects.map((object) => (
        <PolicyObjectTag key={object.id} object={object} />
      ))}
    </Tags>
  </div>
);

export default PolicyObjectsGroup;
