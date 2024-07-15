import { useStore, useDispatch } from '@hooks';
import { ExpandableRowComponent, IconButton, Table, TableCell } from '@uikit';
import ClusterActionHostGroupsTableExpandedContent from './ClusterActionHostGroupsTableExpandedContent';
import { columns } from './ClusterActionHostGroupsTable.constants';
import { isShowSpinner } from '@uikit/Table/Table.utils';
import { AdcmActionHostGroup } from '@models/adcm/actionHostGroup';
import { deleteClusterActionHostGroup } from '@store/adcm/entityActionHostGroups/actionHostGroupsSlice';
import { useState } from 'react';
import ExpandDetailsCell from '@commonComponents/ExpandDetailsCell/ExpandDetailsCell';

const ClusterActionHostGroupsTable = () => {
  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const actionHostGroups = useStore(({ adcm }) => adcm.clusterActionHostGroups.actionHostGroups);
  const isLoading = useStore(({ adcm }) => isShowSpinner(adcm.clusterActionHostGroups.loadState));

  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
  };

  const handleRunClick = () => {
    console.info('run');
  };

  const handleEditClick = () => {
    console.info('edit');
  };

  const handleDeleteClick = (group: AdcmActionHostGroup) => {
    if (cluster) {
      // Confirm dialog?
      dispatch(deleteClusterActionHostGroup({ clusterId: cluster.id, actionHostGroupId: group.id }));
    }
  };

  return (
    <Table isLoading={isLoading} columns={columns} variant="secondary">
      {actionHostGroups.map((group: AdcmActionHostGroup) => {
        return (
          <ExpandableRowComponent
            key={group.id}
            colSpan={columns.length}
            isExpanded={expandableRows[group.id] || false}
            isInactive={group.hosts.length === 0}
            expandedContent={<ClusterActionHostGroupsTableExpandedContent children={group.hosts || []} />}
          >
            <TableCell>{group.name}</TableCell>
            <TableCell>{group.description}</TableCell>
            <ExpandDetailsCell handleExpandRow={() => handleExpandClick(group.id)}>
              {group.hosts.length}
            </ExpandDetailsCell>
            <TableCell hasIconOnly align="center">
              <IconButton
                icon="g1-actions"
                size={32}
                title="run"
                onClick={handleRunClick}
                tooltipProps={{ placement: 'bottom-start' }}
              />
              <IconButton
                icon="g1-edit"
                size={32}
                title="edit"
                onClick={handleEditClick}
                tooltipProps={{ placement: 'bottom-start' }}
              />
              <IconButton
                icon="g1-delete"
                size={32}
                title="delete"
                onClick={() => handleDeleteClick(group)}
                tooltipProps={{ placement: 'bottom-start' }}
              />
            </TableCell>
          </ExpandableRowComponent>
        );
      })}
    </Table>
  );
};

export default ClusterActionHostGroupsTable;
