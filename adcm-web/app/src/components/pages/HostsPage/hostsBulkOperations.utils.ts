import type { AdcmHost } from '@models/adcm';
import type { AdcmDynamicAction } from '@models/adcm/dynamicAction';
import { isBlockingConcernPresent } from '@utils/concernUtils';

export const isHostLinked = (host: AdcmHost) => !!host.cluster?.id;

export const isHostDuplicateLinked = (host: AdcmHost) => host.duplicates.some((dup) => !!dup.cluster?.id);

export const isHostDeletable = (host: AdcmHost) => !isHostLinked(host) && !isHostDuplicateLinked(host);

export const isHostUnlinkable = (host: AdcmHost) => isHostLinked(host);

export const isHostLinkable = (host: AdcmHost) => !isHostLinked(host);

export const canBulkUnlink = (hosts: AdcmHost[]) => hosts.length > 0 && hosts.every(isHostUnlinkable);

export const canBulkLink = (hosts: AdcmHost[]) => hosts.length > 0 && hosts.every(isHostLinkable);

export const canBulkDelete = (hosts: AdcmHost[]) => hosts.length > 0 && hosts.every(isHostDeletable);

export const haveSameHostProvider = (hosts: AdcmHost[]) =>
  hosts.length > 0 && hosts.every((host) => host.hostprovider.id === hosts[0].hostprovider.id);

export const canBulkRunActions = (hosts: AdcmHost[]) =>
  hosts.length > 0 && haveSameHostProvider(hosts) && hosts.every((host) => !isBlockingConcernPresent(host.concerns));

export const BULK_ACTIONS_DISABLED_TITLE = 'Select hosts from the same provider to enable these actions.';

export interface CommonHostAction {
  name: string;
  displayName: string;
  actionIdsByHostId: Record<number, number>;
  disabledReason: string | null;
}

type HostActionsByName = Map<string, AdcmDynamicAction>;

const getHostActionsByName = (
  hostId: number,
  hostDynamicActions: Record<number, AdcmDynamicAction[]>,
): HostActionsByName => {
  const actions = hostDynamicActions[hostId] ?? [];

  return new Map(actions.map((action) => [action.name, action]));
};

const getSharedActionNames = (hostActionMaps: HostActionsByName[]): string[] => {
  const [firstHostActions, ...otherHostActions] = hostActionMaps;

  return [...firstHostActions.keys()].filter((actionName) =>
    otherHostActions.every((hostActions) => hostActions.has(actionName)),
  );
};

const toCommonHostAction = (
  actionName: string,
  hosts: AdcmHost[],
  hostActionMaps: HostActionsByName[],
): CommonHostAction => {
  const actionIdsByHostId: Record<number, number> = {};
  let disabledReason: string | null = null;

  hosts.forEach((host, index) => {
    const action = hostActionMaps[index].get(actionName)!;

    actionIdsByHostId[host.id] = action.id;
    disabledReason = disabledReason ?? action.startImpossibleReason;
  });

  const { displayName } = hostActionMaps[0].get(actionName)!;

  return {
    name: actionName,
    displayName,
    actionIdsByHostId,
    disabledReason,
  };
};

export const getCommonHostActions = (
  hosts: AdcmHost[],
  hostDynamicActions: Record<number, AdcmDynamicAction[]>,
): CommonHostAction[] => {
  if (hosts.length === 0) {
    return [];
  }

  const hostActionMaps = hosts.map((host) => getHostActionsByName(host.id, hostDynamicActions));
  const sharedActionNames = getSharedActionNames(hostActionMaps);

  return sharedActionNames.map((actionName) => toCommonHostAction(actionName, hosts, hostActionMaps));
};

export interface BulkOperationsState {
  hasSameProvider: boolean;
  hasBlockingConcern: boolean;
  commonActions: CommonHostAction[];
  isActionsDisabled: boolean;
  actionsDisabledTitle?: string;
}

export const getBulkOperationsState = (
  hosts: AdcmHost[],
  hostDynamicActions: Record<number, AdcmDynamicAction[]>,
): BulkOperationsState => {
  const hasSameProvider = haveSameHostProvider(hosts);
  const hasBlockingConcern = hosts.some((host) => isBlockingConcernPresent(host.concerns));
  const canRunActions = canBulkRunActions(hosts);
  const commonActions = canRunActions ? getCommonHostActions(hosts, hostDynamicActions) : [];

  return {
    hasSameProvider,
    hasBlockingConcern,
    commonActions,
    isActionsDisabled: !canRunActions || commonActions.length === 0,
    actionsDisabledTitle: !hasSameProvider ? BULK_ACTIONS_DISABLED_TITLE : undefined,
  };
};
