import { useMemo, useState } from 'react';
import { SearchInput, Tag, Tags } from '@uikit';
import s from './AccessManagerRolesTableExpandedContent.module.scss';
import type { AdcmRole } from '@models/adcm';
import { AdcmRoleType } from '@models/adcm';
import { useStore } from '@hooks';
import AccessManagerRolesTableProducts from '../AccessManagerRolesTableProducts/AccessManagerRolesTableProducts';

export interface AccessManagerRolesTableExpandedContentProps {
  rolesChidlren: AdcmRole[];
}

const AccessManagerRolesTableExpandedContent = ({ rolesChidlren }: AccessManagerRolesTableExpandedContentProps) => {
  const products = useStore((s) => s.adcm.roles.relatedData.categories);

  const [productsSelected, setProductsSelected] = useState(products);
  const [textEntered, setTextEntered] = useState('');

  const rolesFiltered = useMemo(() => {
    return rolesChidlren
      .filter((role) => {
        if (role.type !== AdcmRoleType.Business) {
          return false;
        }
        // when selected some products
        if (productsSelected.length > 0) {
          // show roles for products
          return role.isAnyCategory || role.categories.some((cat) => productsSelected.includes(cat));
        }

        // in this case show not products roles
        return !role.isAnyCategory && role.categories.length === 0;
      })
      .filter((role) => role.displayName.toLowerCase().includes(textEntered.toLowerCase()));
  }, [rolesChidlren, productsSelected, textEntered]);

  if (!rolesChidlren.length) return null;

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
      {rolesFiltered.length > 0 && (
        <Tags className={s.content__tags}>
          {rolesFiltered.map((c) => (
            <Tag key={c.id}>{c.displayName}</Tag>
          ))}
        </Tags>
      )}
    </div>
  );
};

export default AccessManagerRolesTableExpandedContent;
