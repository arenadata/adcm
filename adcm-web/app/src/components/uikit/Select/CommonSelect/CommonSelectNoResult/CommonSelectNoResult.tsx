import React from 'react';
import s from './CommonSelectNoResult.module.scss';

const CommonSelectNoResult: React.FC = () => (
  <div className={s.commonSelectNoResult} data-test="no-options">
    No results found
  </div>
);
export default CommonSelectNoResult;
