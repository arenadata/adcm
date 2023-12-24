import React from 'react';
import { IconButton } from '@uikit';
import { useDispatch } from '@hooks';
import { firstUpperCase } from '@utils/stringUtils';
import { AdcmHost } from '@models/adcm';
import { openLinkDialog, openUnlinkDialog } from '@store/adcm/hosts/hostsActionsSlice';

enum linkIcons {
  Link = 'g1-link',
  Unlink = 'g1-unlink',
}

interface LinkHostProps {
  host: AdcmHost;
}

const UnlinkHostToggleButton: React.FC<LinkHostProps> = ({ host }) => {
  const dispatch = useDispatch();
  const linkMode = host.cluster?.id ? 'Unlink' : 'Link';

  const handleLinkClick = () => {
    if (host.cluster?.id) {
      dispatch(openUnlinkDialog(host.id));
    } else {
      dispatch(openLinkDialog(host.id));
    }
  };

  return (
    <IconButton icon={linkIcons[linkMode]} size={32} title={`${firstUpperCase(linkMode)}`} onClick={handleLinkClick} />
  );
};

export default UnlinkHostToggleButton;
