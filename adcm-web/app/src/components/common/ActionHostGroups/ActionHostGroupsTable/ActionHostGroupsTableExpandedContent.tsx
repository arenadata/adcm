import type React from 'react';
import { useMemo, useState } from 'react';
import { SearchInput, Tag, Tags } from '@uikit';
import type { AdcmActionHostGroupHost } from '@models/adcm/actionHostGroup';
import s from './ActionHostGroupsTableExpandedContent.module.scss';

export interface ServiceComponentsTableExpandedContentProps {
  actionHostGroupHosts: AdcmActionHostGroupHost[];
}

const ActionHostGroupsTableExpandedContent = ({ actionHostGroupHosts }: ServiceComponentsTableExpandedContentProps) => {
  const [textEntered, setTextEntered] = useState('');

  const childrenFiltered = useMemo(() => {
    return actionHostGroupHosts.filter((host) => host.name.toLowerCase().includes(textEntered.toLowerCase()));
  }, [actionHostGroupHosts, textEntered]);

  if (!actionHostGroupHosts.length) return null;

  const handleHostsNameFilter = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTextEntered(event.target.value);
  };

  return (
    <div className={s.actionHostGroupsTableExpandedContent}>
      <SearchInput placeholder="Search hosts" value={textEntered} onChange={handleHostsNameFilter} />
      {childrenFiltered.length > 0 && (
        <Tags className={s.actionHostGroupsTableExpandedContent__tags}>
          {childrenFiltered.map((child) => (
            <Tag key={child.id}>{child.name}</Tag>
          ))}
        </Tags>
      )}
    </div>
  );
};

export default ActionHostGroupsTableExpandedContent;
