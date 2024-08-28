import { useMemo, useState } from 'react';
import { Button, ButtonGroup, ToolbarPanel, Checkbox, SearchInput, Tag } from '@uikit';
import type { AdcmActionHostGroup, AdcmDynamicActionRunConfig } from '@models/adcm';
import dialogStyles from '../../DynamicActionDialog.module.scss';
import s from './DynamicActionAgreeActionHostsGroup.module.scss';
import cn from 'classnames';

interface DynamicActionAgreeActionHostsGroupProps {
  actionHostGroup: AdcmActionHostGroup;
  onNext: (changes: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
}

const DynamicActionAgreeActionHostsGroup = ({
  actionHostGroup,
  onNext,
  onCancel,
}: DynamicActionAgreeActionHostsGroupProps) => {
  const [isAgree, setIsAgree] = useState(false);
  const [hostNameFilter, setHostNameFilter] = useState('');

  const handleAgreeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setIsAgree(event.target.checked);
  };

  const handleHostNameFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setHostNameFilter(e.target.value);
  };

  const handleFilterReset = () => {
    setHostNameFilter('');
  };

  const handleNextClick = () => {
    onNext({});
  };

  const filteredHosts = useMemo(() => {
    if (hostNameFilter === '') {
      return actionHostGroup.hosts;
    }
    return actionHostGroup.hosts.filter(
      (x) => x.name.toLocaleLowerCase().indexOf(hostNameFilter.toLocaleLowerCase()) !== -1,
    );
  }, [hostNameFilter, actionHostGroup.hosts]);

  return (
    <div className={s.dynamicActionAgreeActionHostsGroup}>
      <ToolbarPanel className={dialogStyles.dynamicActionDialog__toolbar}>
        <div className={s.dynamicActionAgreeActionHostsGroup__filter}>
          <SearchInput value={hostNameFilter} onChange={handleHostNameFilterChange} />
          <Button variant="tertiary" iconLeft="g1-return" onClick={handleFilterReset} />
        </div>
        <ButtonGroup>
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button disabled={!isAgree} onClick={handleNextClick}>
            Next
          </Button>
        </ButtonGroup>
      </ToolbarPanel>

      <div className={s.dynamicActionAgreeActionHostsGroup__content}>
        <div className={cn(s.dynamicActionAgreeActionHostsGroup__hosts, 'scroll')}>
          {filteredHosts.map((h) => (
            <Tag>{h.name}</Tag>
          ))}
        </div>
        <div className={dialogStyles.dynamicActionDialog__footer}>
          <Checkbox checked={isAgree} label="I agree to run action on these hosts" onChange={handleAgreeChange} />
        </div>
      </div>
    </div>
  );
};

export default DynamicActionAgreeActionHostsGroup;
