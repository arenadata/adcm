import { useMemo } from 'react';
import { Tag, Tags } from '@uikit';
import s from './AccessManagerPoliciesTableExpandedContent.module.scss';
import type { AdcmPolicyObject } from '@models/adcm';

export interface AccessManagerPoliciesTableExpandedContentProps {
  objects: AdcmPolicyObject[];
}

const AccessManagerPoliciesTableExpandedContent = ({ objects }: AccessManagerPoliciesTableExpandedContentProps) => {
  const objectsPrepared = useMemo(
    () => objects.reduce((acc, n) => acc.set(n.type, [...(acc.get(n.type) ?? []), n]), new Map()),
    [objects],
  );

  if (!objects.length) return null;

  return (
    <div className={s.content}>
      {[...objectsPrepared].map(([key, objects]) => (
        <div key={key}>
          <div className={s.content__title}>{key}</div>
          {objects.length > 0 && (
            <Tags className={s.content__tags}>
              {objects.map((object: AdcmPolicyObject) => (
                <Tag key={object.id}>{object.displayName}</Tag>
              ))}
            </Tags>
          )}
        </div>
      ))}
    </div>
  );
};

export default AccessManagerPoliciesTableExpandedContent;
