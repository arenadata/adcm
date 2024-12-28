import type { AdcmJobObject } from '@models/adcm';
import { TableCell } from '@uikit';
import { Link } from 'react-router-dom';
import s from './JobObjectsCell.module.scss';
import { getJobObjectsAdvanced } from './JobObjectsCell.utils';

export interface ObjectsCellProps {
  objects: AdcmJobObject[];
}

const JobObjectsCell = ({ objects }: ObjectsCellProps) => {
  const objectsAdvanced = getJobObjectsAdvanced(objects);
  return (
    <TableCell className={s.jobObjectsCell}>
      {objectsAdvanced.map((object) => {
        return (
          <span key={object.id + object.type}>
            <Link to={object.link} className="text-link">
              {object.name}
            </Link>
          </span>
        );
      })}
    </TableCell>
  );
};

export default JobObjectsCell;
