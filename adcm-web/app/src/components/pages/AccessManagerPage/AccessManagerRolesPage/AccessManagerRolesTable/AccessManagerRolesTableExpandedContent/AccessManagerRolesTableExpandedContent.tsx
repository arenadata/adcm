import { Checkbox, SearchInput, Tags } from '@uikit';
import s from './AccessManagerRolesTableExpandedContent.module.scss';
import { AdcmRole } from '@models/adcm';
import MappingItemTag from '@pages/cluster/ClusterMapping/MappingItemTag/MappingItemTag';
import { useStore } from '@hooks';

export interface AccessManagerRolesTableExpandedContentProps {
  children: AdcmRole[] | null;
}

const handleSearchChange = () => {
  // dispatch();
};

const AccessManagerRolesTableExpandedContent = ({ children }: AccessManagerRolesTableExpandedContentProps) => {
  const products = useStore((s) => s.adcm.roles.products);

  if (!children?.length) return null;

  return (
    <div className={s.content}>
      <br />
      <div className={s.content__checkboxes}>
        <Checkbox key="all" label="All products" checked={true} />
        {products.length && products.map((p) => <Checkbox key={p.id} label={p.name} checked={true} />)}
      </div>
      <div className={s.content__title}>Permissions</div>
      <SearchInput placeholder="Search permissions" variant="primary" onChange={handleSearchChange} />
      {children.length > 0 && (
        <Tags className={s.content__tags}>
          {children.map((c) => (
            <MappingItemTag key={c.id} id={c.id} label={c.displayName} />
          ))}
        </Tags>
      )}
    </div>
  );
};

export default AccessManagerRolesTableExpandedContent;
