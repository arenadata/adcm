import type {
  Batch,
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmSubJob,
  AdcmActionHostGroup,
  AdcmActionHostGroupHost,
  GetAdcmClusterActionHostGroupsArgs,
  GetAdcmClusterActionHostGroupArgs,
  CreateAdcmClusterActionHostGroupArgs,
  DeleteAdcmClusterActionHostGroupArgs,
  GetAdcmClusterActionHostGroupActionsArgs,
  GetAdcmClusterActionHostGroupActionArgs,
  RunAdcmClusterActionHostGroupActionArgs,
  GetAdcmClusterActionHostGroupsHostCandidatesArgs,
  GetAdcmClusterActionHostGroupHostCandidatesArgs,
  GetAdcmClusterActionHostGroupHostsArgs,
  AddAdcmClusterActionHostGroupHostArgs,
  DeleteAdcmClusterActionHostGroupHostArgs,
  NewAdcmActionHostGroup,
  AdcmDynamicActionRunConfig,
} from '@models/adcm';

export type ActionHostGroupOwner = 'cluster' | 'service' | 'component';

type ClusterArgs = {
  clusterId: number;
};

type ServiceArgs = {
  clusterId: number;
  serviceId: number;
};

type ComponentArgs = {
  clusterId: number;
  serviceId: number;
  componentId: number;
};

type SomeEntityArgs = ClusterArgs | ServiceArgs | ComponentArgs;

export type EntityArgs<T extends ActionHostGroupOwner> = T extends 'cluster'
  ? ClusterArgs
  : T extends 'service'
    ? ServiceArgs
    : T extends 'component'
      ? ComponentArgs
      : never;

// Slice Actions Payloads
export type GetActionHostGroupsActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
};

export type OpenCreateDialogActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
};

export type LoadCreateDialogRelatedDataActionPayload = OpenCreateDialogActionPayload;

export type CreateActionHostGroupActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
  actionHostGroup: NewAdcmActionHostGroup;
  hostIds: Set<number>;
};

export type OpenEditDialogActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
  actionHostGroup: AdcmActionHostGroup;
};

export type LoadEditDialogRelatedDataActionPayload = OpenEditDialogActionPayload;

export type UpdateActionHostGroupActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
  actionHostGroup: AdcmActionHostGroup;
  hostIds: Set<number>;
};

export type OpenDeleteDialogActionPayload = {
  actionHostGroup: AdcmActionHostGroup;
};

export type DeleteActionHostGroupActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
  actionHostGroup: AdcmActionHostGroup;
};

export type GetActionHostGroupDynamicActionsActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
  actionHostGroupIds: number[];
};

export type GetActionHostGroupDynamicActionDetailsActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
  actionHostGroupId: number;
  actionId: number;
};

export type OpenDynamicActionActionPayload = GetActionHostGroupDynamicActionDetailsActionPayload;

export type RunActionHostGroupDynamicActionActionPayload = {
  entityType: ActionHostGroupOwner;
  entityArgs: SomeEntityArgs;
  actionHostGroupId: number;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
};

// Api Args
type SomeEntityApiArgs<T> = SomeEntityArgs & Omit<T, 'clusterId'>;

// CRUD
export type GetAdcmActionHostGroupsArgs = SomeEntityApiArgs<GetAdcmClusterActionHostGroupsArgs>;
export type GetAdcmActionHostGroupArgs = SomeEntityApiArgs<GetAdcmClusterActionHostGroupArgs>;
export type CreateAdcmActionHostGroupArgs = SomeEntityApiArgs<CreateAdcmClusterActionHostGroupArgs>;
export type DeleteAdcmActionHostGroupArgs = SomeEntityApiArgs<DeleteAdcmClusterActionHostGroupArgs>;

// Actions
export type GetAdcmActionHostGroupActionsArgs = SomeEntityApiArgs<GetAdcmClusterActionHostGroupActionsArgs>;
export type GetAdcmActionHostGroupActionArgs = SomeEntityApiArgs<GetAdcmClusterActionHostGroupActionArgs>;
export type RunAdcmActionHostGroupActionArgs = SomeEntityApiArgs<RunAdcmClusterActionHostGroupActionArgs>;

// Hosts candidates
export type GetAdcmActionHostGroupsHostCandidatesArgs =
  SomeEntityApiArgs<GetAdcmClusterActionHostGroupsHostCandidatesArgs>;
export type GetAdcmActionHostGroupHostCandidatesArgs =
  SomeEntityApiArgs<GetAdcmClusterActionHostGroupHostCandidatesArgs>;

// Hosts
export type GetAdcmActionHostGroupHostsArgs = SomeEntityApiArgs<GetAdcmClusterActionHostGroupHostsArgs>;
export type AddAdcmActionHostGroupHostArgs = SomeEntityApiArgs<AddAdcmClusterActionHostGroupHostArgs>;
export type DeleteAdcmActionHostGroupHostArgs = SomeEntityApiArgs<DeleteAdcmClusterActionHostGroupHostArgs>;

export interface ActionHostGroupApi {
  // CRUD
  getActionHostGroups(args: GetAdcmActionHostGroupsArgs): Promise<Batch<AdcmActionHostGroup>>;
  getActionHostGroup(args: GetAdcmActionHostGroupArgs): Promise<AdcmActionHostGroup>;
  postActionHostGroup(args: CreateAdcmActionHostGroupArgs): Promise<AdcmActionHostGroup>;
  deleteActionHostGroup(args: DeleteAdcmActionHostGroupArgs): Promise<void>;
  // Actions
  getActionHostGroupActions(args: GetAdcmActionHostGroupActionsArgs): Promise<AdcmDynamicAction[]>;
  getActionHostGroupAction(args: GetAdcmActionHostGroupActionArgs): Promise<AdcmDynamicActionDetails>;
  postActionHostGroupAction(args: RunAdcmActionHostGroupActionArgs): Promise<AdcmSubJob>;
  // Host candidates
  getActionHostGroupsHostCandidates(
    args: GetAdcmActionHostGroupsHostCandidatesArgs,
  ): Promise<AdcmActionHostGroupHost[]>;
  getActionHostGroupHostCandidates(args: GetAdcmActionHostGroupHostCandidatesArgs): Promise<AdcmActionHostGroupHost[]>;
  // Hosts
  getActionHostGroupHosts(args: GetAdcmActionHostGroupHostsArgs): Promise<Batch<AdcmActionHostGroupHost>>;
  postActionHostGroupHost(args: AddAdcmActionHostGroupHostArgs): Promise<AdcmActionHostGroupHost>;
  deleteActionHostGroupHost(args: DeleteAdcmActionHostGroupHostArgs): Promise<void>;
}
