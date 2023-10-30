import { useEffect, useMemo } from 'react';
import { AnchorBar, AnchorBarItem, AnchorList, Button, MarkerIcon, SearchInput, Switch, Text } from '@uikit';
import { useClusterMapping } from '../useClusterMapping';
import ComponentContainer from './ComponentContainer/ComponentContainer';
import ClusterMappingToolbar from '../ClusterMappingToolbar/ClusterMappingToolbar';
import s from './ComponentsMapping.module.scss';
import cn from 'classnames';
import { Link, useParams } from 'react-router-dom';
import { saveMapping } from '@store/adcm/cluster/mapping/mappingSlice';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import RequiredServicesDialog from '@pages/cluster/ClusterMapping/ComponentsMapping/RequiredServicesDialog/RequiredServicesDialog';
import { AdcmEntitySystemState, AdcmMaintenanceMode } from '@models/adcm';

const buildServiceAnchorId = (id: number) => `anchor_${id}`;

const ComponentsMapping = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Mapping' },
          { label: 'Components' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  const {
    hostComponentMapping,
    hosts,
    servicesMapping,
    servicesMappingFilter,
    handleServicesMappingFilterChange,
    mappingState,
    mappingValidation,
    hasSaveError,
    handleMapHostsToComponent,
    handleUnmap,
    handleRevert,
  } = useClusterMapping();

  const anchorItems: AnchorBarItem[] = useMemo(
    () =>
      servicesMapping.map((m) => ({
        label: m.service.displayName,
        id: buildServiceAnchorId(m.service.id),
      })),
    [servicesMapping],
  );

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleServicesMappingFilterChange({ hostName: event.target.value });
  };

  const handleHideEmptyComponentsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleServicesMappingFilterChange({ isHideEmptyComponents: event.target.checked });
  };

  const handleSave = () => {
    dispatch(saveMapping({ clusterId, mapping: hostComponentMapping }));
  };

  return (
    <div className={s.componentsMapping}>
      <ClusterMappingToolbar className={s.componentsMapping__toolbar}>
        <SearchInput placeholder="Search hosts" value={servicesMappingFilter.hostName} onChange={handleFilterChange} />
        <div className={s.componentsMapping__toolbarButtonsAndSwitch}>
          <Switch
            isToggled={servicesMappingFilter.isHideEmptyComponents}
            onChange={handleHideEmptyComponentsChange}
            label="Hide empty components"
          />
          <div className={s.componentsMapping__toolbarButtons}>
            {mappingState !== 'saved' && (
              <Button variant="secondary" onClick={handleRevert}>
                Reset
              </Button>
            )}
            <Button
              onClick={handleSave}
              disabled={mappingState !== 'editing' || !mappingValidation.isAllMappingValid}
              hasError={hasSaveError}
            >
              Save
            </Button>
          </div>
        </div>
      </ClusterMappingToolbar>
      <div className={s.componentsMapping__content}>
        <div data-test="mapping-container">
          {servicesMapping.map(({ service, componentsMapping }) => {
            const isServiceValid = componentsMapping.every(
              (cm) => mappingValidation.byComponents[cm.component.id].isValid,
            );
            const titleClassName = cn(s.serviceMapping__title, {
              [s['serviceMapping__title_error']]: !isServiceValid,
            });

            const markerType = isServiceValid ? 'check' : 'alert';

            return (
              <div key={service.id} className={s.serviceMapping}>
                <Text className={titleClassName} variant="h2" id={buildServiceAnchorId(service.id)}>
                  {service.displayName}
                  <MarkerIcon type={markerType} variant="square" size="medium" />
                </Text>
                {componentsMapping.map((componentMapping) => {
                  const isEditableComponent =
                    componentMapping.component.service.state === AdcmEntitySystemState.Created &&
                    componentMapping.component.maintenanceMode !== AdcmMaintenanceMode.On;

                  return (
                    <ComponentContainer
                      key={componentMapping.component.id}
                      componentMapping={componentMapping}
                      componentMappingValidation={mappingValidation.byComponents[componentMapping.component.id]}
                      filter={servicesMappingFilter}
                      allHosts={hosts}
                      onMap={handleMapHostsToComponent}
                      onUnmap={handleUnmap}
                      allowActions={isEditableComponent ? undefined : []}
                    />
                  );
                })}
              </div>
            );
          })}
          {servicesMapping.length === 0 && (
            <div>
              Add services on the{' '}
              <Link className="text-link" to={`/clusters/${clusterId}/services/`}>
                services page
              </Link>
            </div>
          )}
        </div>
        <AnchorBar>
          <AnchorList items={anchorItems} />
        </AnchorBar>
      </div>

      <RequiredServicesDialog />
    </div>
  );
};

export default ComponentsMapping;
