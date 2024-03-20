import { Table, TableCell, TableRow } from '@uikit';
import React, { useMemo } from 'react';
import { columns } from './BundleOverviewTable.constants';
import { useStore } from '@hooks';
import { encode } from 'js-base64';
import { orElseGet } from '@utils/checkUtils';
import s from './BundleOverviewTable.module.scss';

const BundleOverviewTable: React.FC = () => {
  const bundle = useStore(({ adcm }) => adcm.bundle.bundle);

  const licenseLink = useMemo(() => {
    if (!bundle?.mainPrototype.license.text) return null;

    return encode(bundle.mainPrototype.license.text);
  }, [bundle?.mainPrototype.license.text]);

  return (
    <Table columns={columns} variant="quaternary" className={s.bundleOverviewTable}>
      <TableRow>
        <TableCell>{bundle?.displayName}</TableCell>
        <TableCell>{bundle?.version}</TableCell>
        <TableCell>{orElseGet(bundle?.mainPrototype.license.status)}</TableCell>
        <TableCell>
          {orElseGet(licenseLink, () => {
            return (
              <a href={`data:text/plain;base64,${licenseLink}`} download="EULA.txt">
                EULA.txt
              </a>
            );
          })}
        </TableCell>
      </TableRow>
    </Table>
  );
};

export default BundleOverviewTable;
