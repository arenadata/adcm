import { useState, useRef, useMemo } from 'react';
import { Tags } from '@uikit';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import MappingItemTag from '../../MappingItemTag/MappingItemTag';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import { AdcmHostShortView, AdcmComponent } from '@models/adcm';
import { HostMapping } from '../../ClusterMapping.types';
import s from './HostContainer.module.scss';

export interface HostContainerProps {
  hostMapping: HostMapping;
  allComponents: AdcmComponent[];
  onMap: (components: AdcmComponent[], host: AdcmHostShortView) => void;
  onUnmap: (hostId: number, componentId: number) => void;
}

const HostContainer = ({ hostMapping, allComponents, onMap, onUnmap }: HostContainerProps) => {
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);
  const componentsOptions = useMemo(() => getOptionsFromArray(allComponents, (c) => c.displayName), [allComponents]);
  const { host, components: hostComponents } = hostMapping;

  const handleAdd = () => {
    setIsSelectOpen(true);
  };

  const handleDelete = (e: React.MouseEvent<HTMLButtonElement>) => {
    const componentId = Number(e.currentTarget.dataset.id);
    onUnmap(host.id, componentId);
  };

  const handleMappingChange = (components: AdcmComponent[]) => {
    onMap(components, host);
  };

  return (
    <>
      <div className={s.hostContainer}>
        <div className={s.hostContainerHeader}>
          <span className={s.hostContainerHeader__title}>{host.name}</span>
          <span className={s.hostContainerHeader__count}>{hostComponents.length}</span>
          <AddMappingButton
            className={s.hostContainerHeader__add}
            ref={addIconRef}
            label="Add components"
            onAddClick={handleAdd}
          />
        </div>
        {hostComponents.length > 0 && (
          <Tags className={s.hostContainer__components}>
            {hostComponents.map((c) => (
              <MappingItemTag key={c.id} id={c.id} label={c.displayName} onDeleteClick={handleDelete} />
            ))}
          </Tags>
        )}
      </div>
      <MappingItemSelect
        isOpen={isSelectOpen}
        checkAllLabel="All components"
        searchPlaceholder="Search components"
        options={componentsOptions}
        value={hostComponents}
        onChange={handleMappingChange}
        onOpenChange={setIsSelectOpen}
        triggerRef={addIconRef}
      />
    </>
  );
};

export default HostContainer;
