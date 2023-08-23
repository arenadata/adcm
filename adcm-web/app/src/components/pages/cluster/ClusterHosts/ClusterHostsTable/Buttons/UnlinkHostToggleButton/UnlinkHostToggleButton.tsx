import React from 'react';
import { IconButton, Tooltip } from '@uikit';
import { useDispatch } from '@hooks';
import { AdcmHost } from '@models/adcm';
import { openUnlinkDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';

interface LinkHostProps {
  host: AdcmHost;
}

const UnlinkHostToggleButton: React.FC<LinkHostProps> = ({ host }) => {
  const dispatch = useDispatch();

  const handleLinkClick = () => {
    if (host.cluster?.id) {
      dispatch(openUnlinkDialog(host.id));
    }
  };

  return (
    <Tooltip label="Unlink host">
      <IconButton icon="g1-unlink" size={32} onClick={handleLinkClick} />
    </Tooltip>
  );
};

export default UnlinkHostToggleButton;
