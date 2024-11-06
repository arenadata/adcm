import React from 'react';
import { IconButton } from '@uikit';
import { useDispatch } from '@hooks';
import { AdcmHost } from '@models/adcm';
import { openUnlinkDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';

interface LinkHostProps {
  host: AdcmHost;
}

const UnlinkHostToggleButton: React.FC<LinkHostProps> = ({ host }) => {
  const dispatch = useDispatch();

  const handleLinkClick = () => {
    if (host) {
      dispatch(openUnlinkDialog(host));
    }
  };

  return <IconButton icon="g1-unlink" size={32} title="Unlink" onClick={handleLinkClick} />;
};

export default UnlinkHostToggleButton;
