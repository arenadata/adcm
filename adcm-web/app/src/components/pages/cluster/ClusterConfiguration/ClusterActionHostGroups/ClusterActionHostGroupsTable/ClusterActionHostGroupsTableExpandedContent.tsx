import React, { useMemo, useState } from 'react';
import { SearchInput, Tag, Tags } from '@uikit';
import type { AdcmActionHostGroupHost } from '@models/adcm/actionHostGroup';
import s from './ClusterActionHostGroupsTableExpandedContent.module.scss';

export interface ServiceComponentsTableExpandedContentProps {
  children: AdcmActionHostGroupHost[];
}

const ClusterActionHostGroupsTableExpandedContent = ({ children }: ServiceComponentsTableExpandedContentProps) => {
  const [textEntered, setTextEntered] = useState('');

  const childrenFiltered = useMemo(() => {
    return children.filter((child) => child.name.toLowerCase().includes(textEntered.toLowerCase()));
  }, [children, textEntered]);

  if (!children.length) return null;

  const handleHostsNameFilter = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTextEntered(event.target.value);
  };

  return (
    <div className={s.clusterActionHostGroupsTableExpandedContent}>
      <SearchInput placeholder="Search hosts" value={textEntered} onChange={handleHostsNameFilter} />
      {childrenFiltered.length > 0 && (
        <Tags className={s.clusterActionHostGroupsTableExpandedContent__tags}>
          {childrenFiltered.map((child) => (
            <Tag key={child.id} children={child.name} />
          ))}
        </Tags>
      )}
    </div>
  );
};

export default ClusterActionHostGroupsTableExpandedContent;
