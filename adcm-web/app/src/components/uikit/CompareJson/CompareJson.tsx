import type React from 'react';
import ReactJsonViewCompare from 'react-json-view-compare';
import type { JSONObject } from '@models/json';
import './CompareJson.scss';

interface CompareJsonProps {
  oldData: JSONObject;
  newData: JSONObject;
}

const CompareJson: React.FC<CompareJsonProps> = ({ oldData, newData }) => {
  return <ReactJsonViewCompare oldData={oldData} newData={newData} />;
};

export default CompareJson;
