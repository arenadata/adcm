import { ExpandableRowComponent, IconButton, Table, TableCell } from '@uikit';
import ActionHostGroupDynamicActionsIconButton from './ActionHostGroupDynamicActionsIconButton';
import ActionHostGroupsTableExpandedContent from './ActionHostGroupsTableExpandedContent';
import { columns } from './ActionHostGroupsTable.constants';
import type { EntitiesDynamicActions } from '@models/adcm';
import type { AdcmActionHostGroup } from '@models/adcm/actionHostGroup';
import { useState } from 'react';
import ExpandDetailsCell from '@commonComponents/ExpandDetailsCell/ExpandDetailsCell';
import ActionHostGroupTableFooter from '../ActionHostGroupTableFooter/ActionHostGroupFooter';

export interface ActionHostGroupsTableProps {
  // action host group not independent entity
  // is parent entity have some concerns then we can't run dynamic actions on actions groups
  isDynamicActionsDisabled: boolean;
  actionHostGroups: AdcmActionHostGroup[];
  dynamicActions: EntitiesDynamicActions;
  isLoading: boolean;
  onOpenDynamicActionDialog: (actionHostGroup: AdcmActionHostGroup, actionId: number) => void;
  onOpenEditDialog: (actionHostGroup: AdcmActionHostGroup) => void;
  onOpenDeleteDialog: (actionHostGroup: AdcmActionHostGroup) => void;
}

const ActionHostGroupsTable = ({
  actionHostGroups,
  dynamicActions,
  isDynamicActionsDisabled,
  isLoading,
  onOpenDynamicActionDialog,
  onOpenEditDialog,
  onOpenDeleteDialog,
}: ActionHostGroupsTableProps) => {
  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
  };

  return (
    <>
      <Table isLoading={isLoading} columns={columns} variant="secondary">
        {actionHostGroups.map((actionHostGroup: AdcmActionHostGroup) => {
          return (
            <ExpandableRowComponent
              key={actionHostGroup.id}
              colSpan={columns.length}
              isExpanded={expandableRows[actionHostGroup.id] || false}
              isInactive={actionHostGroup.hosts.length === 0}
              expandedContent={<ActionHostGroupsTableExpandedContent children={actionHostGroup.hosts || []} />}
            >
              <TableCell>{actionHostGroup.name}</TableCell>
              <TableCell>{actionHostGroup.description}</TableCell>
              <ExpandDetailsCell
                isDisabled={actionHostGroup.hosts.length === 0}
                handleExpandRow={() => handleExpandClick(actionHostGroup.id)}
              >
                {actionHostGroup.hosts.length}
              </ExpandDetailsCell>
              <TableCell hasIconOnly align="center">
                <ActionHostGroupDynamicActionsIconButton
                  isDisabled={isDynamicActionsDisabled}
                  dynamicActions={dynamicActions[actionHostGroup.id]}
                  onActionSelect={(actionId: number) => onOpenDynamicActionDialog(actionHostGroup, actionId)}
                />
                <IconButton
                  icon="g1-edit"
                  size={32}
                  title="Edit"
                  onClick={() => onOpenEditDialog(actionHostGroup)}
                  tooltipProps={{ placement: 'bottom-start' }}
                />
                <IconButton
                  icon="g1-delete"
                  size={32}
                  title="Delete"
                  onClick={() => onOpenDeleteDialog(actionHostGroup)}
                  tooltipProps={{ placement: 'bottom-start' }}
                />
              </TableCell>
            </ExpandableRowComponent>
          );
        })}
      </Table>
      <ActionHostGroupTableFooter />
    </>
  );
};

export default ActionHostGroupsTable;
