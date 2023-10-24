import React from 'react';
import { Link } from 'react-router-dom';

interface LinkToLicenseTextProps {
  bundleId: number;
}

const LinkToLicenseText: React.FC<LinkToLicenseTextProps> = ({ bundleId }) => {
  return (
    <Link className="text-link" to={`/bundles/${bundleId}`} target="_blank">
      Terms of Agreement
    </Link>
  );
};

export default LinkToLicenseText;
