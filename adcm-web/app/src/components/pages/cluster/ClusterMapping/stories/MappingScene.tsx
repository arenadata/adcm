import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import { MemoryRouter, Link } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import {
  AdcmHostComponentMapRuleAction,
  AdcmMaintenanceMode,
  type AdcmDynamicActionDetails,
  type AdcmHostShortView,
  type AdcmMapping,
  type AdcmMappingComponent,
  type AdcmMappingComponentService,
  type NotAddedServicesDictionary,
} from '@models/adcm';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard';
import { Button, DialogV2 } from '@uikit';
import LicenseAcceptanceList from '@commonComponents/license/LicenseAcceptanceList/LicenseAcceptanceList';
import {
  checkComponentActionsMappingAvailability,
  checkHostActionsMappingAvailability,
  checkHostActionsUnmappingAvailability,
  sortExtendedComponentsMapping,
} from '@commonComponents/DynamicActionDialog/DynamicActionSteps/DynamicActionHostMapping/DynamicActionHostMapping.utils';
import ActionWizardComponentsMapping from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardComponentsMapping/ActionWizardComponentsMapping';
import ActionWizardHostsMapping from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardHostsMapping/ActionWizardHostsMapping';
import {
  checkComponentMappingAvailability,
  checkHostMappingAvailability,
  checkHostUnmappingAvailability,
} from '../ClusterMapping.utils';
import { useClusterMapping } from '../useClusterMapping';
import type {
  ComponentsMappingErrors,
  HostMapping,
  InitiallyMappedComponentsDictionary,
  InitiallyMappedHostsDictionary,
  MappingFilter,
  ServiceMapping,
} from '../ClusterMapping.types';
import ComponentContainer from '../ComponentsMapping/ComponentContainer/ComponentContainer';
import ComponentContainerV2 from '../ComponentsMapping/ComponentContainer/ComponentContainerV2';
import HostContainer from '../HostsMapping/HostContainer/HostContainer';
import HostsMapping from '../HostsMapping/HostsMapping';
import HostsMappingV2 from '../HostsMapping/HostsMappingV2';
import Service from '../ComponentsMapping/Service/Service';
import ServiceV2 from '../ComponentsMapping/Service/ServiceV2';
import ShowServices from '../RequiredServicesDialog/ShowServices/ShowServices';
import {
  components as defaultComponents,
  createStoryComponent,
  createStoryHost,
  createStoryService,
  hdfsServicePrototype,
  hosts as defaultHosts,
  zkServerDependingOnHdfs,
} from './fixtures/mappingStoryFixtures';
import type { MappingDialogVariant, MappingLayoutVariant, MappingStoryKind } from './mappingStory.types';
import { MappingLayersV2Toggle } from './MappingLayersV2Toggle';
import { useMappingLayersV2 } from '@hooks/useMappingLayersV2';
import { useMappingEditor } from '@hooks/useMappingEditor';
import { getRulesForComponent } from '@utils/mapping/mappingRules';
import type { ComponentHostRelations, MappingViewConfig } from '@utils/mapping/mapping.types';
import ActionWizardComponentsMappingV2 from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardComponentsMapping/ActionWizardComponentsMappingV2';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';

export type MappingSceneView = MappingStoryKind;

export type MappingSceneProps = {
  description?: string;
  view: MappingSceneView;
  pairs?: AdcmMapping[];
  hosts?: AdcmHostShortView[];
  components?: AdcmMappingComponent[];
  notAddedServicesDictionary?: NotAddedServicesDictionary;
  focusComponentName?: string;
  focusHostName?: string;
  layout?: MappingLayoutVariant;
  dialog?: MappingDialogVariant;
  showEntityControls?: boolean;
  rules?: AdcmActionProcessMappingStepRules[];
  hostsPreviewMode?: boolean;
};

const EMPTY_MAPPING: AdcmMapping[] = [];
const EMPTY_NOT_ADDED: NotAddedServicesDictionary = {};

const frameStyle: CSSProperties = {
  width: '100%',
  maxWidth: 960,
  padding: 16,
};

const toolbarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  marginBottom: 16,
};

const Frame = ({
  description,
  layersV2,
  onLayersChange,
  children,
}: {
  description?: string;
  layersV2: boolean;
  onLayersChange: (enabled: boolean) => void;
  children: ReactNode;
}) => (
  <div style={frameStyle}>
    <MappingLayersV2Toggle enabled={layersV2} onEnabledChange={onLayersChange} />
    {description ? <p>{description}</p> : null}
    {children}
  </div>
);

const addRemoveRules = (component: string, service: string): AdcmActionProcessMappingStepRules[] => [
  {
    operation: AdcmHostComponentMapRuleAction.Add,
    component,
    service,
    description: '',
    required: false,
  },
  {
    operation: AdcmHostComponentMapRuleAction.Remove,
    component,
    service,
    description: '',
    required: false,
  },
];

const defaultWizardRules: AdcmActionProcessMappingStepRules[] = addRemoveRules('zk_server', 'zookeeper');

const toActionDetails = (rules: AdcmActionProcessMappingStepRules[]): AdcmDynamicActionDetails => ({
  id: 0,
  name: 'story-action',
  displayName: 'Story action',
  isAllowToTerminate: false,
  disclaimer: '',
  hostComponentMapRules: rules.map((rule) => ({
    action: rule.operation,
    service: rule.service,
    component: rule.component,
  })),
  configuration: null,
  startImpossibleReason: '',
  processes: null,
});

const createdServiceOf = (components: AdcmMappingComponent[]): AdcmMappingComponentService | undefined => {
  const created = components.find((c) => c.service.state === 'created');
  return created?.service ?? components.at(-1)?.service;
};

const rulesToStrategy = (rules: AdcmActionProcessMappingStepRules[]) =>
  rules.map((rule) => ({
    service: rule.service,
    component: rule.component,
    operation: rule.operation,
  }));

const withExtras = (
  servicesMapping: ServiceMapping[],
  addedServices: AdcmMappingComponentService[],
): ServiceMapping[] => {
  const byId = new Map(servicesMapping.map((sm) => [sm.service.id, sm]));
  const extras = addedServices
    .filter((service) => !byId.has(service.id))
    .map((service) => ({ service, componentsMapping: [], hasErrors: false }));
  return [...servicesMapping, ...extras];
};

type EntityControlsProps = {
  show: boolean;
  addHost: () => void;
  addMmHost: () => void;
  addService: () => void;
  addComponent: () => void;
};

const EntityControls = ({ show, addHost, addMmHost, addService, addComponent }: EntityControlsProps) => {
  if (!show) {
    return null;
  }

  return (
    <div style={toolbarStyle}>
      <Button variant="secondary" onClick={addHost}>
        Add host
      </Button>
      <Button variant="secondary" onClick={addMmHost}>
        Add host in MM
      </Button>
      <Button variant="secondary" onClick={addService}>
        Add service
      </Button>
      <Button variant="secondary" onClick={addComponent}>
        Add component
      </Button>
    </div>
  );
};

type SharedEntity = {
  hosts: AdcmHostShortView[];
  components: AdcmMappingComponent[];
  addedServices: AdcmMappingComponentService[];
  rules: AdcmActionProcessMappingStepRules[];
  addHost: () => void;
  addMmHost: () => void;
  addService: () => void;
  addComponent: () => void;
};

type ContentProps = MappingSceneProps &
  SharedEntity & {
    layersV2: boolean;
    onLayersChange: (enabled: boolean) => void;
  };

type MappingApi = {
  hostsMapping: HostMapping[];
  servicesMapping: ServiceMapping[];
  servicesMappingForView: ServiceMapping[];
  mappingErrors: ComponentsMappingErrors;
  mappingFilter: MappingFilter;
  initiallyMappedHosts?: InitiallyMappedHostsDictionary;
  initiallyMappedComponents?: InitiallyMappedComponentsDictionary;
  handleMapHostsToComponent: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  handleMapComponentsToHost: (components: AdcmMappingComponent[], host: AdcmHostShortView) => void;
  handleUnmap: (hostId: number, componentId: number) => void;
  flatComponents: Array<{
    component: AdcmMappingComponent;
    hosts: AdcmHostShortView[];
    allowedActions?: Set<AdcmHostComponentMapRuleAction>;
  }>;
  strategyRules: ReturnType<typeof rulesToStrategy>;
  useActionRulesChecks: boolean;
};

const buildBodies = (
  api: MappingApi,
  entity: SharedEntity,
  entityControls: ReactNode,
  hostsPreviewMode: boolean,
): { clusterBody: ReactNode; hostsBody: ReactNode; wizardBody: ReactNode; actionBody: ReactNode } => {
  const {
    hostsMapping,
    servicesMappingForView,
    mappingErrors,
    mappingFilter,
    initiallyMappedHosts,
    initiallyMappedComponents,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    flatComponents,
    strategyRules,
    useActionRulesChecks,
  } = api;
  const { hosts, components, rules } = entity;

  const clusterBody = (
    <>
      {entityControls}
      {servicesMappingForView.map((sm) => (
        <Service
          key={sm.service.id}
          service={sm.service}
          componentsMapping={sm.componentsMapping}
          hasErrors={sm.hasErrors}
          anchorId={`anchor_${sm.service.id}`}
          hosts={hosts}
          mappingFilter={mappingFilter}
          mappingErrors={mappingErrors}
          initiallyMappedHosts={initiallyMappedHosts ?? {}}
          onMap={handleMapHostsToComponent}
          onUnmap={handleUnmap}
          onInstallServices={() => undefined}
        />
      ))}
    </>
  );

  const hostsBody = (
    <>
      {entityControls}
      <HostsMapping
        components={components}
        hostsMapping={hostsMapping}
        mappingErrors={mappingErrors}
        mappingFilter={mappingFilter}
        onMap={handleMapComponentsToHost}
        onUnmap={handleUnmap}
        onInstallServices={() => undefined}
        checkComponentMappingAvailability={checkComponentMappingAvailability}
        checkHostMappingAvailability={(host, component) => {
          let initMappedHosts: Set<number> | undefined;
          if (component?.id) {
            initMappedHosts = initiallyMappedHosts?.[component.id];
          } else if (initiallyMappedComponents?.[host.id]?.size) {
            initMappedHosts = new Set([host.id]);
          }
          return checkHostMappingAvailability(host, initMappedHosts);
        }}
        checkHostUnmappingAvailability={(host, component) => {
          let initMappedHosts: Set<number> | undefined;
          if (component?.id) {
            initMappedHosts = initiallyMappedHosts?.[component.id];
          } else if (initiallyMappedComponents?.[host.id]?.size) {
            initMappedHosts = new Set([host.id]);
          }
          return checkHostUnmappingAvailability(host, initMappedHosts);
        }}
      />
    </>
  );

  const wizardBody = hostsPreviewMode ? (
    <>
      {entityControls}
      <ActionWizardHostsMapping
        servicesMapping={servicesMappingForView}
        components={components}
        hostsMapping={hostsMapping}
        mappingFilter={mappingFilter}
        mappingErrors={mappingErrors}
        onMap={handleMapComponentsToHost}
        onUnmap={handleUnmap}
        onInstallServices={() => undefined}
        initiallyMappedHosts={initiallyMappedHosts ?? {}}
        initiallyMappedComponents={initiallyMappedComponents ?? {}}
        rules={rules}
      />
    </>
  ) : (
    <>
      {entityControls}
      <ActionWizardComponentsMapping
        clusterId={1}
        hosts={hosts}
        servicesMapping={servicesMappingForView}
        mappingErrors={mappingErrors}
        mappingFilter={mappingFilter}
        initiallyMappedHosts={initiallyMappedHosts ?? {}}
        rules={rules}
        sortDirection="asc"
        onMap={handleMapHostsToComponent}
        onUnmap={handleUnmap}
        onClose={() => undefined}
      />
    </>
  );

  const actionBody = (
    <>
      {entityControls}
      <div className={s.dynamicActionDialog__componentWrapper}>
        {flatComponents.length === 0 ? (
          <div>
            Add services on the{' '}
            <Link className="text-link" to="/clusters/1/services">
              services page
            </Link>
          </div>
        ) : (
          flatComponents.map((componentMapping) => {
            const allowActions =
              componentMapping.allowedActions ??
              (useActionRulesChecks
                ? getRulesForComponent(strategyRules, componentMapping.component)
                : new Set<AdcmHostComponentMapRuleAction>());

            return (
              <ComponentContainer
                key={componentMapping.component.id}
                componentMapping={componentMapping}
                filter={mappingFilter}
                allHosts={hosts}
                mappingErrors={mappingErrors[componentMapping.component.id]}
                onMap={handleMapHostsToComponent}
                onUnmap={handleUnmap}
                checkComponentMappingAvailability={(component) =>
                  checkComponentActionsMappingAvailability(component, allowActions)
                }
                checkHostMappingAvailability={(host) =>
                  checkHostActionsMappingAvailability(
                    host,
                    allowActions,
                    initiallyMappedHosts?.[componentMapping.component.id],
                  )
                }
                checkHostUnmappingAvailability={(host) =>
                  checkHostActionsUnmappingAvailability(
                    host,
                    allowActions,
                    initiallyMappedHosts?.[componentMapping.component.id],
                  )
                }
              />
            );
          })
        )}
      </div>
    </>
  );

  return { clusterBody, hostsBody, wizardBody, actionBody };
};

const buildBodiesV2 = (
  api: MappingApi,
  entity: SharedEntity,
  entityControls: ReactNode,
  hostsPreviewMode: boolean,
  relations: ComponentHostRelations,
): { clusterBody: ReactNode; hostsBody: ReactNode; wizardBody: ReactNode; actionBody: ReactNode } => {
  const {
    hostsMapping,
    servicesMappingForView,
    mappingErrors,
    mappingFilter,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    flatComponents,
  } = api;
  const { hosts, components } = entity;

  const clusterBody = (
    <>
      {entityControls}
      {servicesMappingForView.map((sm) => (
        <ServiceV2
          key={sm.service.id}
          service={sm.service}
          componentsMapping={sm.componentsMapping}
          hasErrors={sm.hasErrors}
          anchorId={`anchor_${sm.service.id}`}
          hosts={hosts}
          mappingFilter={mappingFilter}
          mappingErrors={mappingErrors}
          relations={relations}
          onMap={handleMapHostsToComponent}
          onUnmap={handleUnmap}
          onInstallServices={() => undefined}
        />
      ))}
    </>
  );

  const hostsBody = (
    <>
      {entityControls}
      <HostsMappingV2
        components={components}
        hostsMapping={hostsMapping}
        mappingErrors={mappingErrors}
        mappingFilter={mappingFilter}
        onMap={handleMapComponentsToHost}
        onUnmap={handleUnmap}
        onInstallServices={() => undefined}
        relations={relations}
      />
    </>
  );

  const wizardBody = hostsPreviewMode ? (
    <>
      {entityControls}
      <HostsMappingV2
        components={components}
        hostsMapping={hostsMapping}
        mappingFilter={mappingFilter}
        mappingErrors={mappingErrors}
        onMap={handleMapComponentsToHost}
        onUnmap={handleUnmap}
        onInstallServices={() => undefined}
        relations={relations}
      />
    </>
  ) : (
    <>
      {entityControls}
      <ActionWizardComponentsMappingV2
        clusterId={1}
        hosts={hosts}
        servicesMapping={servicesMappingForView}
        mappingErrors={mappingErrors}
        mappingFilter={mappingFilter}
        onMap={handleMapHostsToComponent}
        onUnmap={handleUnmap}
        onClose={() => undefined}
        relations={relations}
      />
    </>
  );

  const actionBody = (
    <>
      {entityControls}
      <div className={s.dynamicActionDialog__componentWrapper}>
        {flatComponents.length === 0 ? (
          <div>
            Add services on the{' '}
            <Link className="text-link" to="/clusters/1/services">
              services page
            </Link>
          </div>
        ) : (
          flatComponents.map((componentMapping) => (
            <ComponentContainerV2
              key={componentMapping.component.id}
              componentMapping={componentMapping}
              filter={mappingFilter}
              allHosts={hosts}
              mappingErrors={mappingErrors[componentMapping.component.id]}
              onMap={handleMapHostsToComponent}
              onUnmap={handleUnmap}
              relations={relations}
            />
          ))
        )}
      </div>
    </>
  );

  return { clusterBody, hostsBody, wizardBody, actionBody };
};

const SceneViews = ({
  description,
  view,
  layout,
  focusComponentName,
  focusHostName,
  layersV2,
  onLayersChange,
  hosts,
  components,
  api,
  entityControls,
  clusterBody,
  hostsBody,
  wizardBody,
  actionBody,
}: {
  description?: string;
  view: MappingSceneView;
  layout?: MappingLayoutVariant;
  focusComponentName?: string;
  focusHostName?: string;
  layersV2: boolean;
  onLayersChange: (enabled: boolean) => void;
  hosts: AdcmHostShortView[];
  components: AdcmMappingComponent[];
  api: MappingApi;
  entityControls: ReactNode;
  clusterBody: ReactNode;
  hostsBody: ReactNode;
  wizardBody: ReactNode;
  actionBody: ReactNode;
}) => {
  const {
    hostsMapping,
    servicesMapping,
    mappingErrors,
    mappingFilter,
    initiallyMappedHosts,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
  } = api;

  const layoutView = layout ?? 'cluster_az';
  const isWizard = view === 'wizard' || (view === 'layout' && layoutView === 'wizard_editable_first');
  const isAction = view === 'action' || (view === 'layout' && layoutView === 'action_flat');
  const isClusterLayout = view === 'layout' && layoutView === 'cluster_az';

  if (isWizard) {
    return (
      <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
        {wizardBody}
      </Frame>
    );
  }

  if (isAction) {
    return (
      <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
        {actionBody}
      </Frame>
    );
  }

  if (view === 'componentsMode' || isClusterLayout) {
    return (
      <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
        {clusterBody}
      </Frame>
    );
  }

  if (view === 'hostsMode') {
    return (
      <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
        {hostsBody}
      </Frame>
    );
  }

  if (view === 'host') {
    const hostMapping = hostsMapping.find((hm) => hm.host.name === focusHostName);
    if (!hostMapping) {
      return (
        <Frame layersV2={layersV2} onLayersChange={onLayersChange}>
          <div>Host {focusHostName} not found</div>
        </Frame>
      );
    }

    return (
      <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
        {entityControls}
        <HostContainer
          hostMapping={hostMapping}
          mappingErrors={mappingErrors}
          filter={mappingFilter}
          allComponents={components}
          onMap={handleMapComponentsToHost}
          onUnmap={handleUnmap}
          checkHostAvailability={(host) => {
            if (hostMapping.components.length === 0) {
              return checkHostMappingAvailability(host);
            }
            return checkHostUnmappingAvailability(host);
          }}
          checkComponentMappingAvailability={(component) => {
            const { componentNotAvailableError } = checkComponentMappingAvailability(component);
            return (
              componentNotAvailableError ??
              checkHostMappingAvailability(hostMapping.host, initiallyMappedHosts?.[component.id])
            );
          }}
          checkComponentUnmappingAvailability={(component) => {
            const { componentNotAvailableError } = checkComponentMappingAvailability(component);
            return (
              componentNotAvailableError ??
              checkHostUnmappingAvailability(hostMapping.host, initiallyMappedHosts?.[component.id])
            );
          }}
        />
      </Frame>
    );
  }

  const componentMapping = servicesMapping
    .flatMap((sm) => sm.componentsMapping)
    .find((cm) => cm.component.name === focusComponentName);

  if (view === 'component' && !componentMapping) {
    return (
      <Frame layersV2={layersV2} onLayersChange={onLayersChange}>
        <div>Component {focusComponentName} not found</div>
      </Frame>
    );
  }

  if (view === 'component' && componentMapping) {
    return (
      <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
        {entityControls}
        <ComponentContainer
          componentMapping={componentMapping}
          mappingErrors={mappingErrors[componentMapping.component.id]}
          filter={mappingFilter}
          allHosts={hosts}
          onMap={handleMapHostsToComponent}
          onUnmap={handleUnmap}
          onInstallServices={() => undefined}
          checkComponentMappingAvailability={checkComponentMappingAvailability}
          checkHostMappingAvailability={(host) =>
            checkHostMappingAvailability(host, initiallyMappedHosts?.[componentMapping.component.id])
          }
          checkHostUnmappingAvailability={(host) =>
            checkHostUnmappingAvailability(host, initiallyMappedHosts?.[componentMapping.component.id])
          }
        />
      </Frame>
    );
  }

  return (
    <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
      {clusterBody}
    </Frame>
  );
};

const MappingSceneLegacyContent = (props: ContentProps) => {
  const {
    description,
    view,
    pairs = EMPTY_MAPPING,
    notAddedServicesDictionary = EMPTY_NOT_ADDED,
    focusComponentName,
    focusHostName,
    layout,
    showEntityControls = true,
    hosts,
    components,
    addedServices,
    rules,
    addHost,
    addMmHost,
    addService,
    addComponent,
    layersV2,
    onLayersChange,
    hostsPreviewMode = false,
  } = props;

  const {
    hostsMapping,
    servicesMapping,
    mappingErrors,
    mappingFilter,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    initiallyMappedHosts,
    initiallyMappedComponents,
  } = useClusterMapping(pairs, hosts, components, notAddedServicesDictionary, true);

  const servicesMappingForView = useMemo(
    () => withExtras(servicesMapping, addedServices),
    [addedServices, servicesMapping],
  );

  const actionDetails = useMemo(() => toActionDetails(rules), [rules]);
  const flatComponents = useMemo(
    () => sortExtendedComponentsMapping(servicesMappingForView, actionDetails),
    [servicesMappingForView, actionDetails],
  );

  const api: MappingApi = {
    hostsMapping,
    servicesMapping,
    servicesMappingForView,
    mappingErrors,
    mappingFilter,
    initiallyMappedHosts,
    initiallyMappedComponents,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    flatComponents,
    strategyRules: rulesToStrategy(rules),
    useActionRulesChecks: false,
  };

  const entityControls = (
    <EntityControls
      show={showEntityControls && view !== 'dialog'}
      addHost={addHost}
      addMmHost={addMmHost}
      addService={addService}
      addComponent={addComponent}
    />
  );

  const bodies = buildBodies(api, props, entityControls, hostsPreviewMode);

  return (
    <SceneViews
      description={description}
      view={view}
      layout={layout}
      focusComponentName={focusComponentName}
      focusHostName={focusHostName}
      layersV2={layersV2}
      onLayersChange={onLayersChange}
      hosts={hosts}
      components={components}
      api={api}
      entityControls={entityControls}
      {...bodies}
    />
  );
};

const MappingSceneV2Content = (props: ContentProps) => {
  const {
    description,
    view,
    pairs = EMPTY_MAPPING,
    notAddedServicesDictionary = EMPTY_NOT_ADDED,
    focusComponentName,
    focusHostName,
    layout,
    showEntityControls = true,
    hosts,
    components,
    addedServices,
    rules,
    addHost,
    addMmHost,
    addService,
    addComponent,
    layersV2,
    onLayersChange,
    hostsPreviewMode = false,
  } = props;

  const layoutView = layout ?? 'cluster_az';
  const isWizard = view === 'wizard' || (view === 'layout' && layoutView === 'wizard_editable_first');
  const isAction = view === 'action' || (view === 'layout' && layoutView === 'action_flat');
  const isHostsKind = view === 'hostsMode' || view === 'host';

  const viewConfig = useMemo((): MappingViewConfig => {
    if (isAction) {
      return {
        strategy: { type: 'actionRules', rules: rulesToStrategy(rules) },
        kind: 'flat',
        sort: 'editableFirst',
      };
    }
    if (isWizard) {
      return {
        strategy: { type: 'actionRules', rules: rulesToStrategy(rules) },
        kind: hostsPreviewMode ? 'hosts' : 'services',
        sort: 'editableFirst',
      };
    }
    if (isHostsKind) {
      return {
        strategy: { type: 'cluster' },
        kind: 'hosts',
        sort: 'name',
      };
    }
    return {
      strategy: { type: 'cluster' },
      kind: 'services',
      sort: 'name',
    };
  }, [isAction, isWizard, isHostsKind, hostsPreviewMode, rules]);

  const {
    hostsMapping,
    servicesMapping,
    mappingErrors,
    mappingFilter,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    viewModel,
    relations,
  } = useMappingEditor(pairs, hosts, components, notAddedServicesDictionary, true, viewConfig);

  const servicesFromVm = viewModel?.kind === 'services' ? viewModel.services : servicesMapping;
  const hostsFromVm = viewModel?.kind === 'hosts' ? viewModel.hosts : hostsMapping;
  const flatFromVm = viewModel?.kind === 'flat' ? viewModel.components : [];

  const servicesMappingForView = useMemo(
    () => withExtras(servicesFromVm, addedServices),
    [addedServices, servicesFromVm],
  );

  const api: MappingApi = {
    hostsMapping: hostsFromVm,
    servicesMapping: servicesFromVm,
    servicesMappingForView,
    mappingErrors,
    mappingFilter,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    flatComponents: flatFromVm,
    strategyRules: rulesToStrategy(rules),
    useActionRulesChecks: true,
  };

  const entityControls = (
    <EntityControls
      show={showEntityControls && view !== 'dialog'}
      addHost={addHost}
      addMmHost={addMmHost}
      addService={addService}
      addComponent={addComponent}
    />
  );

  if (!relations) {
    return null;
  }

  const bodies = buildBodiesV2(api, props, entityControls, hostsPreviewMode, relations);

  return (
    <SceneViews
      description={description}
      view={view}
      layout={layout}
      focusComponentName={focusComponentName}
      focusHostName={focusHostName}
      layersV2={layersV2}
      onLayersChange={onLayersChange}
      hosts={hosts}
      components={components}
      api={api}
      entityControls={entityControls}
      {...bodies}
    />
  );
};

const MappingSceneDialog = ({
  description,
  dialog,
  layersV2,
  onLayersChange,
}: {
  description?: string;
  dialog?: MappingDialogVariant;
  layersV2: boolean;
  onLayersChange: (enabled: boolean) => void;
}) => {
  const dependsServices = zkServerDependingOnHdfs.dependOn?.map((d) => d.servicePrototype) ?? [];

  if (dialog === 'license_step') {
    return (
      <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
        <DialogV2
          title="Required objects"
          actionButtonLabel="Apply"
          onAction={() => undefined}
          onCancel={() => undefined}
        >
          <LicenseAcceptanceList
            items={[
              {
                id: hdfsServicePrototype.id,
                displayName: hdfsServicePrototype.displayName,
                license: hdfsServicePrototype.license,
              },
            ]}
            onAccept={() => undefined}
          />
        </DialogV2>
      </Frame>
    );
  }

  const store = configureStore({
    reducer: {
      adcm: () => ({
        clusterMapping: {
          requiredServicesDialog: { component: zkServerDependingOnHdfs },
        },
      }),
    },
  });

  return (
    <Provider store={store}>
      <Frame description={description} layersV2={layersV2} onLayersChange={onLayersChange}>
        <DialogV2
          title="Required objects"
          actionButtonLabel="Apply"
          onAction={() => undefined}
          onCancel={() => undefined}
        >
          <ShowServices dependsServices={dependsServices} unacceptedSelectedServices={dependsServices} />
        </DialogV2>
      </Frame>
    </Provider>
  );
};

const MappingSceneInner = (props: MappingSceneProps) => {
  const {
    view,
    hosts: initialHosts = defaultHosts,
    components: initialComponents = defaultComponents,
    rules: initialRules = defaultWizardRules,
    showEntityControls = true,
  } = props;

  const [layersV2, setLayersV2] = useMappingLayersV2();
  const idRef = useRef(10_000);
  const [hosts, setHosts] = useState(initialHosts);
  const [components, setComponents] = useState(initialComponents);
  const [addedServices, setAddedServices] = useState<AdcmMappingComponentService[]>([]);
  const [rules, setRules] = useState(initialRules);

  useEffect(() => {
    setHosts(initialHosts);
    setComponents(initialComponents);
    setAddedServices([]);
    setRules(initialRules);
  }, [initialHosts, initialComponents, initialRules]);

  const addHost = useCallback(() => {
    const id = idRef.current++;
    setHosts((prev) => [...prev, createStoryHost(id, `host-${id}`)]);
  }, []);

  const addMmHost = useCallback(() => {
    const id = idRef.current++;
    setHosts((prev) => [...prev, createStoryHost(id, `mm-host-${id}`, AdcmMaintenanceMode.On)]);
  }, []);

  const addService = useCallback(() => {
    const serviceId = idRef.current++;
    const slug = `svc_${serviceId}`;
    const service = createStoryService(serviceId, slug, `Service ${serviceId}`);
    setAddedServices((prev) => [...prev, service]);
  }, []);

  const addComponent = useCallback(() => {
    const service = addedServices.at(-1) ?? createdServiceOf(components);
    if (!service) {
      addService();
      return;
    }
    const componentId = idRef.current++;
    const component = createStoryComponent(componentId, `cmp_${componentId}`, `Component ${componentId}`, service, [
      0,
      '+',
    ]);
    setComponents((prev) => [...prev, component]);
    setRules((prev) => [...prev, ...addRemoveRules(component.name, service.name)]);
  }, [addService, addedServices, components]);

  if (view === 'dialog') {
    return (
      <MappingSceneDialog
        description={props.description}
        dialog={props.dialog}
        layersV2={layersV2}
        onLayersChange={setLayersV2}
      />
    );
  }

  const contentProps: ContentProps = {
    ...props,
    showEntityControls,
    hosts,
    components,
    addedServices,
    rules,
    addHost,
    addMmHost,
    addService,
    addComponent,
    layersV2,
    onLayersChange: setLayersV2,
  };

  return layersV2 ? <MappingSceneV2Content {...contentProps} /> : <MappingSceneLegacyContent {...contentProps} />;
};

export const MappingScene = (props: MappingSceneProps) => (
  <MemoryRouter>
    <MappingSceneInner {...props} />
  </MemoryRouter>
);
