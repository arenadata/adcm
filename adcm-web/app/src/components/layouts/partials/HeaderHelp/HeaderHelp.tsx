import type React from 'react';
import { useState } from 'react';
import IconButton from '@uikit/IconButton/IconButton';
import ActionMenu from '@uikit/ActionMenu/ActionMenu';
import { Link } from 'react-router-dom';
import { ConditionalWrapper, Tooltip } from '@uikit';
import AboutAdcmModal from './AboutAdcm/AboutAdcmModal/AboutAdcmModal';
import type { DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import { apiRedocHost, HelperLinkActions } from '@constants';

const LinkItem = <T,>(props: DefaultSelectListItemProps<T>) => {
  const {
    option: { value, label, title },
    className,
  } = props;

  if (typeof value !== 'string') return <li />;

  return (
    <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} placement="bottom-start">
      <li className={className}>
        <Link to={value.toString()} target="_blank" rel="noopener noreferrer" className="flex-block">
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
  {
    value: `${apiRedocHost}/api/v2/schema/redoc/`,
    label: 'ADCM API',
    ItemComponent: LinkItem,
  },
];

const HeaderHelp: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const handleOpenModal = (value: string | null) => {
    if (value === 'aboutAdcm') {
      setIsOpen(true);
    }
  };

  const handleCloseModal = () => {
    setIsOpen(false);
  };

  return (
    <>
      <ActionMenu placement="bottom-end" value={null} onChange={handleOpenModal} options={linkOptions}>
        <IconButton icon="g2-info" size={28} />
      </ActionMenu>
      <AboutAdcmModal isOpen={isOpen} onCancel={handleCloseModal} />
    </>
  );
};

export default HeaderHelp;
