import React, { useState } from 'react';
import IconButton from '@uikit/IconButton/IconButton';
import ActionMenu from '@uikit/ActionMenu/ActionMenu';
import { Link } from 'react-router-dom';
import { ConditionalWrapper, Tooltip } from '@uikit';
import AboutAdcm from './AboutAdcm/AboutAdcm.tsx';
import AboutAdcmModal from './AboutAdcm/AboutAdcmModal/AboutAdcmModal.tsx';
import { DefaultSelectListItemProps } from '@uikit/Select/SingleSelect/SingleSelectList/SingleSelectList.tsx';

enum HelperLinkActions {
  Help = 'https://t.me/arenadata_cm',
  Documentation = 'https://docs.arenadata.io/en/ADCM/current/introduction/intro.html',
}

const LinkItem = <T,>(props: DefaultSelectListItemProps<T>) => {
  const {
    option: { value, label, title },
    className,
  } = props;

  if (typeof value !== 'string') return <li></li>;

  return (
    <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} placement="bottom-start">
      <li className={className}>
        <Link to={value.toString()} target="_blank" className="flex-block">
          {label}
        </Link>
      </li>
    </ConditionalWrapper>
  );
};

const linkOptions = [
  {
    value: 'aboutAdcm',
    label: 'About ADCM',
    ItemComponent: AboutAdcm,
  },
  {
    value: HelperLinkActions.Help,
    label: 'Help',
    ItemComponent: LinkItem,
  },
  {
    value: HelperLinkActions.Documentation,
    label: 'Documentation',
    ItemComponent: LinkItem,
  },
];

const HeaderHelp: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const openModal = (value: string | null) => {
    if (value === 'aboutAdcm') {
      setIsOpen(true);
    }
  };

  return (
    <>
      <ActionMenu placement="bottom-end" value={null} onChange={openModal} options={linkOptions}>
        <IconButton icon="g2-info" size={28} />
      </ActionMenu>
      <AboutAdcmModal isOpen={isOpen} onOpenChange={setIsOpen} />
    </>
  );
};

export default HeaderHelp;
