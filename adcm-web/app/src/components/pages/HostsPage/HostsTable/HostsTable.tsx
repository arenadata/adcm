import type React from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { Button, Checkbox, ExpandableRowComponent, IconButton, Table, TableCell, FlexGroup } from '@uikit';
import StatusableCell from '@commonComponents/Table/Cells/StatusableCell';
import { columns, hostStatusesMap } from '@pages/HostsPage/HostsTable/HostsTable.constants';
import { useDispatch, useStore, useSelectedItems, useClipboardCopy } from '@hooks';
import type { AdcmHost } from '@models/adcm/host';
import UnlinkHostToggleButton from '@pages/HostsPage/HostsTable/Buttons/UnlinkHostToggleButton/UnlinkHostToggleButton';
import type { SortParams } from '@uikit/types/list.types';
import { setSortParams } from '@store/adcm/hosts/hostsTableSlice';
import { orElseGet } from '@utils/checkUtils';
import {
  openDeleteDialog,
  openHostSharingDialog,
  openMaintenanceModeDialog,
  openUpdateDialog,
  setSelectedItemsIds as setSelectedHostsIds,
} from '@store/adcm/hosts/hostsActionsSlice';
import MaintenanceModeButton from '@commonComponents/MaintenanceModeButton/MaintenanceModeButton';
import HostDynamicActionsIcon from '../HostDynamicActionsIcon/HostDynamicActionsIcon';
import MultiStateCell from '@commonComponents/Table/Cells/MultiStateCell';
import Concern from '@commonComponents/Concern/Concern';
import { AdcmEntitySystemState } from '@models/adcm';
import { Link } from 'react-router-dom';
import { isShowSpinner } from '@uikit/Table/Table.utils';
import { useCallback, useEffect, useState } from 'react';
import HostsTableExpandedContent from './HostsTableExpandedContent/HostsTableExpandedContent';
import cn from 'classnames';

const getHostUniqKey = ({ id }: AdcmHost) => id;

const HostsTable: React.FC = () => {
  const dispatch = useDispatch();
  const [, handleCopy] = useClipboardCopy();

  const hosts = useStore(({ adcm }) => adcm.hosts.hosts);
  const isLoading = useStore(({ adcm }) => isShowSpinner(adcm.hosts.loadState));
  const sortParams = useStore((s) => s.adcm.hostsTable.sortParams);
  const selectedItemsIds = useStore(({ adcm }) => adcm.hostsActions.selectedItemsIds);
  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});
  const [hostId, setHostId] = useState<number | null>();

  const setSelectedItemsIds = useCallback<Dispatch<SetStateAction<number[]>>>(
    (arg) => {
      const value = typeof arg === 'function' ? arg(selectedItemsIds) : arg;
      dispatch(setSelectedHostsIds(value));
    },
    [dispatch, selectedItemsIds],
  );

  const { isAllItemsSelected, toggleSelectedAllItems, getHandlerSelectedItem, isItemSelected } = useSelectedItems(
    hosts,
    getHostUniqKey,
    selectedItemsIds,
    setSelectedItemsIds,
  );

  const resetExpand = useCallback(() => {
    if (!hostId) return;

    const host = hosts.find(({ id }) => id === hostId);

    if (host && host.id in expandableRows && host.duplicates.length === 0) {
      setExpandableRows({});
    }
  }, [hosts, expandableRows, setExpandableRows]);

  useEffect(() => {
    resetExpand();
  }, [resetExpand]);

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
    setHostId(id);
  };

  const handleClickMaintenanceMode = (host: AdcmHost) => () => {
    if (host.isMaintenanceModeAvailable) {
      dispatch(openMaintenanceModeDialog(host));
    }
  };

  const getHandleDeleteClick = (host: AdcmHost) => () => {
    dispatch(openDeleteDialog([host]));
  };

  const handleUpdateClick = (host: AdcmHost) => {
    dispatch(openUpdateDialog(host));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const getHandleHostSharingDialog = (host: AdcmHost) => () => {
    dispatch(openHostSharingDialog(host));
  };

  return (
    <Table
      isLoading={isLoading}
      columns={columns}
      sortParams={sortParams}
      onSorting={handleSorting}
      variant="secondary"
      isAllSelected={isAllItemsSelected}
      toggleSelectedAll={toggleSelectedAllItems}
    >
      {hosts.map((host: AdcmHost) => {
        const isHostLinked = !!host.cluster?.id;
        const isDuplicateLinked = host.duplicates.some((dup) => dup.cluster?.id);
        const isDisabled = isHostLinked || isDuplicateLinked;
        const entityLabel = (isHostLinked && 'host') || (isDuplicateLinked && 'duplicate');

        return (
          <ExpandableRowComponent
            key={host.id}
            colSpan={columns.length}
            isExpanded={expandableRows[host.id] || false}
            expandedContent={<HostsTableExpandedContent duplicates={host.duplicates} />}
            className={cn({ 'is-selected': selectedItemsIds.includes(host.id) })}
          >
            <TableCell>
              <Checkbox checked={isItemSelected(host)} onChange={getHandlerSelectedItem(host)} />
            </TableCell>
            <StatusableCell
              status={hostStatusesMap[host.status]}
              endAdornment={
                <FlexGroup gap={4} style={{ marginLeft: 8 }}>
                  <IconButton
                    icon="g1-copy"
                    size={20}
                    title="Copy hostname"
                    className="copy-button"
                    onClick={() => handleCopy(host.name)}
                  />
                  {host.state === AdcmEntitySystemState.Created && !isHostLinked && (
                    <IconButton
                      icon="g1-edit"
                      size={32}
                      title="Edit"
                      className="rename-button"
                      onClick={() => handleUpdateClick(host)}
                    />
                  )}
                </FlexGroup>
              }
            >
              <Link to={`/hosts/${host.id}`} className="text-link">
                {host.name}
              </Link>
            </StatusableCell>
            <MultiStateCell entity={host} />
            <TableCell>
              <Link to={`/hostproviders/${host.hostprovider.id}`} className="text-link">
                {host.hostprovider.name}
              </Link>
            </TableCell>
            <TableCell>
              <FlexGroup gap="10px">
                {orElseGet(host.cluster, (cluster) => (
                  <Link to={`/clusters/${cluster.id}`} className="text-link">
                    {cluster.name}
                  </Link>
                ))}
                {host.duplicates.length > 0 && (
                  <Button
                    className={expandableRows[host.id] ? 'is-active' : ''}
                    variant="secondary"
                    iconLeft="dots"
                    onClick={() => handleExpandClick(host.id)}
                  />
                )}
              </FlexGroup>
            </TableCell>
            <TableCell hasIconOnly>
              <Concern concerns={host.concerns} />
            </TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton
                icon="g1-host-sharing"
                size={32}
                onClick={getHandleHostSharingDialog(host)}
                title="Share host"
              />
              <HostDynamicActionsIcon host={host} />
              <MaintenanceModeButton
                isMaintenanceModeAvailable={host.isMaintenanceModeAvailable}
                maintenanceModeStatus={host.maintenanceMode}
                onClick={handleClickMaintenanceMode(host)}
              />
              <UnlinkHostToggleButton host={host} />
              <IconButton
                icon="g1-delete"
                size={32}
                disabled={isDisabled}
                onClick={getHandleDeleteClick(host)}
                title={isDisabled ? `Unlink the ${entityLabel} to enable the Delete button` : 'Delete'}
              />
            </TableCell>
          </ExpandableRowComponent>
        );
      })}
    </Table>
  );
};

export default HostsTable;
