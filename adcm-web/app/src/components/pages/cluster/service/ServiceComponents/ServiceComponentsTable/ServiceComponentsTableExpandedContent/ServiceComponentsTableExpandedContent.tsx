import type React from 'react';
import { useMemo, useState } from 'react';
import { SearchInput, Tag, Tags } from '@uikit';
import s from './ServiceComponentsTableExpandedContent.module.scss';
import type { AdcmServiceComponentHost } from '@models/adcm';

export interface ServiceComponentsTableExpandedContentProps {
  hostComponents: AdcmServiceComponentHost[];
}

const ServiceComponentsTableExpandedContent = ({ hostComponents }: ServiceComponentsTableExpandedContentProps) => {
  const [textEntered, setTextEntered] = useState('');

  const hostComponentsFiltered = useMemo(() => {
    return hostComponents.filter((child) => child.name.toLowerCase().includes(textEntered.toLowerCase()));
  }, [hostComponents, textEntered]);

  if (!hostComponentsFiltered.length) return null;

  const handleHostsNameFilter = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTextEntered(event.target.value);
  };

  return (
    <div className={s.serviceComponentsTableExpandedContent}>
      <SearchInput placeholder="Search hosts" value={textEntered} onChange={handleHostsNameFilter} />
      {hostComponentsFiltered.length > 0 && (
        <Tags className={s.serviceComponentsTableExpandedContent__tags}>
          {hostComponentsFiltered.map((hostComponent) => (
            <Tag key={hostComponent.id}>{hostComponent.name}</Tag>
          ))}
        </Tags>
      )}
    </div>
  );
};

export default ServiceComponentsTableExpandedContent;
