import { useMemo, useState } from 'react';
import { SearchInput, Tag, Tags } from '@uikit';
import s from './AccessManagerRolesTableExpandedContent.module.scss';
import { AdcmRole } from '@models/adcm';
import { useStore } from '@hooks';
import AccessManagerRolesTableProducts from '../AccessManagerRolesTableProducts/AccessManagerRolesTableProducts';

export interface AccessManagerRolesTableExpandedContentProps {
  children: AdcmRole[];
}

const AccessManagerRolesTableExpandedContent = ({ children }: AccessManagerRolesTableExpandedContentProps) => {
  const products = useStore((s) => s.adcm.roles.relatedData.categories);

  const [productsSelected, setProductsSelected] = useState(products);
  const [textEntered, setTextEntered] = useState('');

  const childrenFiltered = useMemo(() => {
    return children
      .filter((child) => child.categories.find((cat) => productsSelected.includes(cat)) || child.isAnyCategory)
      .filter((child) => child.displayName.toLowerCase().includes(textEntered.toLowerCase()));
  }, [children, productsSelected, textEntered]);

  if (!children.length) return null;

  const handleCheckAllClick = (value: string[]) => {
    setProductsSelected(value);
  };

  const handleRoleNameFilter = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTextEntered(event.target.value);
  };

  return (
    <div className={s.content}>
      <br />
      <AccessManagerRolesTableProducts onSelect={handleCheckAllClick} />
      <div className={s.content__title}>Permissions</div>
      <SearchInput placeholder="Search permissions" value={textEntered} onChange={handleRoleNameFilter} />
      {childrenFiltered.length > 0 && (
        <Tags className={s.content__tags}>
          {childrenFiltered.map((c) => (
            <Tag key={c.id} children={c.displayName} />
          ))}
        </Tags>
      )}
    </div>
  );
};

export default AccessManagerRolesTableExpandedContent;
