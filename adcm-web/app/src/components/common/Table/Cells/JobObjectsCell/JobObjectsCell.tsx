import { AdcmJobObject } from '@models/adcm';
import { linkByObjectTypeMap } from '@pages/JobsPage/JobsTable/JobsTable.constants';
import { TableCell } from '@uikit';
import { Link } from 'react-router-dom';
import s from './JobObjectsCell.module.scss';

export interface ObjectsCellProps {
  objects: AdcmJobObject[];
}

const JobObjectsCell = ({ objects }: ObjectsCellProps) => (
  <TableCell className={s.jobObjectsCell}>
    {objects.map((object) => {
      return (
        <span key={object.id + object.type}>
          <Link to={`/${linkByObjectTypeMap[object.type]}/${object.id}`} className="text-link">
            {object.name}
          </Link>
        </span>
      );
    })}
  </TableCell>
);

export default JobObjectsCell;
