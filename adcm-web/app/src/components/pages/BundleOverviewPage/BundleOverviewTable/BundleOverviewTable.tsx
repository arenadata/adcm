import { Table, TableCell, TableRow } from '@uikit';
import React, { useMemo } from 'react';
import { columns } from './BundleOverviewTable.constants';
import { useStore } from '@hooks';
import { encode } from 'js-base64';
import { orElseGet } from '@utils/checkUtils';
import { firstUpperCase } from '@utils/stringUtils';
import s from './BundleOverviewTable.module.scss';

const BundleOverviewTable: React.FC = () => {
  const prototype = useStore(({ adcm }) => adcm.bundle.relatedData.prototype);

  const licenseLink = useMemo(() => {
    if (!prototype?.license.text) return null;

    return encode(prototype.license.text);
  }, [prototype?.license.text]);

  return (
    <Table columns={columns} variant="quaternary" className={s.bundleOverviewTable}>
      <TableRow>
        <TableCell>{prototype?.displayName}</TableCell>
        <TableCell>{prototype?.version}</TableCell>
        <TableCell>{orElseGet(prototype?.license.status, firstUpperCase)}</TableCell>
        <TableCell>
          {orElseGet(licenseLink, () => {
            return (
              // eslint-disable-next-line spellcheck/spell-checker
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
