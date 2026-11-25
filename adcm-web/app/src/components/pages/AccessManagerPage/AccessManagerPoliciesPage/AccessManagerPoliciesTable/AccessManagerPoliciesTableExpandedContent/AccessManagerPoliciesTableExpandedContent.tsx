import { useMemo } from 'react';
import PolicyObjectsGroup from './PolicyObjectsGroup';
import s from './AccessManagerPoliciesTableExpandedContent.module.scss';
import type { AdcmPolicyObject } from '@models/adcm';

export interface AccessManagerPoliciesTableExpandedContentProps {
  objects: AdcmPolicyObject[];
}

const groupObjectsByType = (objects: AdcmPolicyObject[]) =>
  objects.reduce(
    (acc, object) => acc.set(object.type, [...(acc.get(object.type) ?? []), object]),
    new Map<string, AdcmPolicyObject[]>(),
  );

const AccessManagerPoliciesTableExpandedContent = ({ objects }: AccessManagerPoliciesTableExpandedContentProps) => {
  const objectsByType = useMemo(() => groupObjectsByType(objects), [objects]);

  if (!objects.length) return null;

  return (
    <div className={s.content}>
      {[...objectsByType].map(([type, typeObjects]) => (
        <PolicyObjectsGroup key={type} type={type} objects={typeObjects} />
      ))}
    </div>
  );
};

export default AccessManagerPoliciesTableExpandedContent;
