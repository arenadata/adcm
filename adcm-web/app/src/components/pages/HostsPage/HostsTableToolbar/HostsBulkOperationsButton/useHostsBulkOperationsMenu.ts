import { useCallback, useMemo, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import type { AppDispatch } from '@store/store';
import type { AdcmHost } from '@models/adcm';
import { openDeleteDialog, openLinkDialog, openUnlinkDialog } from '@store/adcm/hosts/hostsActionsSlice';
import { openBulkHostDynamicActionDialog } from '@store/adcm/hosts/hostsDynamicActionsSlice';
import {
  canBulkDelete,
  canBulkLink,
  canBulkUnlink,
  getBulkOperationsState,
} from '@pages/HostsPage/hostsBulkOperations.utils';
import type { CommonHostAction } from '@pages/HostsPage/hostsBulkOperations.utils';
import type { BulkOperationsMenuItem } from './BulkOperationsMenu/BulkOperationsMenu';

type BulkOperationDialogAction = (hosts: AdcmHost[]) => { type: string; payload: AdcmHost[] };

interface BulkOperationItem {
  label: string;
  isApplicable: (hosts: AdcmHost[]) => boolean;
  openDialog: BulkOperationDialogAction;
}

const BULK_OPERATION_ITEMS: BulkOperationItem[] = [
  { label: 'Unlink', isApplicable: canBulkUnlink, openDialog: openUnlinkDialog },
  { label: 'Link', isApplicable: canBulkLink, openDialog: openLinkDialog },
  { label: 'Delete', isApplicable: canBulkDelete, openDialog: openDeleteDialog },
];

const createBulkOperationClickHandler = (
  dispatch: AppDispatch,
  selectedHosts: AdcmHost[],
  closeMenu: () => void,
  openDialog: BulkOperationDialogAction,
) => {
  return () => {
    dispatch(openDialog(selectedHosts));
    closeMenu();
  };
};

export const useHostsBulkOperationsMenu = () => {
  const dispatch = useDispatch();
  const [isOpen, setIsOpen] = useState(false);

  const hosts = useStore(({ adcm }) => adcm.hosts.hosts);
  const selectedItemsIds = useStore(({ adcm }) => adcm.hostsActions.selectedItemsIds);
  const hostDynamicActions = useStore(({ adcm }) => adcm.hostsDynamicActions.hostDynamicActions);

  const selectedHosts = useMemo(
    () => hosts.filter((host) => selectedItemsIds.includes(host.id)),
    [hosts, selectedItemsIds],
  );

  const isDisabled = selectedHosts.length === 0;

  const bulkOperationsState = useMemo(
    () => getBulkOperationsState(selectedHosts, hostDynamicActions),
    [selectedHosts, hostDynamicActions],
  );

  const closeMenu = useCallback(() => {
    setIsOpen(false);
  }, []);

  const handleSelectAction = useCallback(
    (action: CommonHostAction) => {
      dispatch(
        openBulkHostDynamicActionDialog({
          hosts: selectedHosts,
          actionName: action.name,
          actionIdsByHostId: action.actionIdsByHostId,
        }),
      );
      closeMenu();
    },
    [closeMenu, dispatch, selectedHosts],
  );

  const menuItems = useMemo<BulkOperationsMenuItem[]>(() => {
    const operationItems = BULK_OPERATION_ITEMS.map(({ label, isApplicable, openDialog }) => ({
      label,
      disabled: !isApplicable(selectedHosts),
      onClick: createBulkOperationClickHandler(dispatch, selectedHosts, closeMenu, openDialog),
    }));

    const actionsItem: BulkOperationsMenuItem = {
      label: 'Actions',
      withDividerBefore: true,
      disabled: bulkOperationsState.isActionsDisabled,
      title: bulkOperationsState.actionsDisabledTitle,
      actions: bulkOperationsState.commonActions,
      onSelectAction: handleSelectAction,
    };

    return [...operationItems, actionsItem];
  }, [bulkOperationsState, closeMenu, dispatch, handleSelectAction, selectedHosts]);

  return {
    isOpen,
    setIsOpen,
    isDisabled,
    menuItems,
  };
};
