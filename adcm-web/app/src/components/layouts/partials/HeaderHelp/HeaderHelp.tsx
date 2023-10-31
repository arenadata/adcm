import React from 'react';
import IconButton from '@uikit/IconButton/IconButton';
import ActionMenu from '@uikit/ActionMenu/ActionMenu';
import { Link } from 'react-router-dom';
import { SelectOption } from '@uikit';

enum HelperLinkActions {
  Help = 'https://t.me/arenadata_cm',
  Documentation = 'https://docs.arenadata.io/en/ADCM/current/introduction/intro.html',
}

const renderItem = ({ value, label }: SelectOption<string>) => {
  return (
    <Link to={value} target="_blank" className="flex-block">
      {label}
    </Link>
  );
};

const emptyCallback = () => {
  //
};

const HeaderHelp: React.FC = () => {
  const linkOptions = [
    {
      value: HelperLinkActions.Help,
      label: 'Help',
    },
    {
      value: HelperLinkActions.Documentation,
      label: 'Documentation',
    },
  ];

  return (
    <ActionMenu
      placement="bottom-end"
      value={null}
      renderItem={renderItem}
      onChange={emptyCallback}
      options={linkOptions}
    >
      <IconButton icon="g2-info" size={28} />
    </ActionMenu>
  );
};

export default HeaderHelp;
