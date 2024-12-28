import { Link } from 'react-router-dom';
import ErrorPageContent from '@commonComponents/ErrorPageContent/ErrorPageContent';
import ErrorTextContainer from '@commonComponents/ErrorPageContent/ErrorTextContainer/ErrorTextContainer';

const NotFoundPage = () => {
  return (
    <>
      <ErrorPageContent errorCode="404">
        <ErrorTextContainer errorHeader="Page not found">
          <div>Page you're trying to reach doesn't exist or was removed.</div>
          <div>
            Please return to{' '}
            <Link className="text-link" to="/">
              Cluster
            </Link>{' '}
            page and try again later
          </div>
        </ErrorTextContainer>
      </ErrorPageContent>
    </>
  );
};

export default NotFoundPage;
