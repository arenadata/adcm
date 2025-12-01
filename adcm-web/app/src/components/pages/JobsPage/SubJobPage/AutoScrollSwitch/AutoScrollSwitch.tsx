import { useSubJobsLogsAutoScrollContext } from '../SubJobLogsAutoScroll/SubJobLogsAutoScroll.context';
import { ExpandableSwitch } from '@uikit';

const AutoScrollSwitch = () => {
  const autoScrollContextValue = useSubJobsLogsAutoScrollContext();

  const handleSwitchToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    autoScrollContextValue?.toggleAutoScroll(e.target.checked);
  };

  return (
    <ExpandableSwitch
      onChange={handleSwitchToggle}
      label="Auto-scroll"
      isToggled={Boolean(autoScrollContextValue?.isAutoScroll)}
    />
  );
};

export default AutoScrollSwitch;
