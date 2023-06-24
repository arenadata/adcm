import React from 'react';
import s from './Copyright.module.scss';

const currentYear = new Date().getFullYear();

const Copyright: React.FC = () => {
  return <div className={s.copyright}>Arenadata LLC, {currentYear}</div>;
};

export default Copyright;
