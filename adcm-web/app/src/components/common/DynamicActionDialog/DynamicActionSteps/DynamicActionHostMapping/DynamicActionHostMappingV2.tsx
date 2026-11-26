import type React from 'react';
import { useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import { Button, ButtonGroup, SearchInput, SpinnerPanel, ToolbarPanel } from '@uikit';
import { getMappings } from '@store/adcm/entityDynamicActions/dynamicActionsMappingSlice';
import { LoadState } from '@models/loadState';
import type { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';
import ComponentContainerV2 from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentContainer/ComponentContainerV2';
import { useDynamicActionMapping } from './useDynamicActionMapping';

interface DynamicActionHostMappingV2Props {
  clusterId: number;
  actionDetails: AdcmDynamicActionDetails;
  configuration?: AdcmDynamicActionRunConfig['configuration'] | null;
  onNext: (changes: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
}

const DynamicActionHostMappingV2: React.FC<DynamicActionHostMappingV2Props> = ({
  clusterId,
  actionDetails,
  onNext,
  onCancel,
}) => {
  const dispatch = useDispatch();

  useEffect(() => {
    if (!Number.isNaN(clusterId)) {
      dispatch(getMappings({ clusterId }));
    }
  }, [clusterId, dispatch]);

  const { hosts, components, mapping, loadState } = useStore(({ adcm }) => adcm.dynamicActionsMapping);
  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clusterMapping.relatedData.notAddedServicesDictionary);

  const {
    localMapping,
    flatComponents,
    mappingFilter,
    handleMappingFilterChange,
    mappingErrors,
    handleMapHostsToComponent,
    handleUnmap,
    handleReset,
    relations,
  } = useDynamicActionMapping(
    mapping,
    hosts,
    components,
    notAddedServicesDictionary,
    loadState === LoadState.Loaded,
    actionDetails,
  );

  const isEmpty = flatComponents.length === 0;

  const handleNext = useCallback(() => {
    onNext({ hostComponentMap: localMapping });
  }, [localMapping, onNext]);

  const handleFilterChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      handleMappingFilterChange({ hostName: event.target.value });
    },
    [handleMappingFilterChange],
  );

  const hasErrors = Object.keys(mappingErrors).length > 0;

  return (
    <div>
      <ToolbarPanel className={s.dynamicActionDialog__toolbar}>
        <SearchInput onChange={handleFilterChange} placeholder="Search host" />
        <ButtonGroup>
          <Button variant="tertiary" iconLeft="g1-return" onClick={handleReset} title="Reset" />
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleNext} disabled={isEmpty || hasErrors} hasError={false}>
            Next
          </Button>
        </ButtonGroup>
      </ToolbarPanel>

      {loadState === LoadState.Loading && <SpinnerPanel />}

      {loadState === LoadState.Loaded && relations && (
        <div className={s.dynamicActionDialog__componentWrapper}>
          {isEmpty && (
            <div>
              Add services on the{' '}
              <Link className="text-link" to={`/clusters/${clusterId}/services`} onClick={onCancel}>
                services page
              </Link>
            </div>
          )}
          {flatComponents.map((componentMapping) => (
            <ComponentContainerV2
              key={componentMapping.component.id}
              componentMapping={componentMapping}
              mappingErrors={mappingErrors[componentMapping.component.id]}
              allHosts={hosts}
              filter={mappingFilter}
              relations={relations}
              onMap={handleMapHostsToComponent}
              onUnmap={handleUnmap}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default DynamicActionHostMappingV2;
