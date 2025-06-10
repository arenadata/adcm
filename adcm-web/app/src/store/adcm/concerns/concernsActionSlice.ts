import { createAsyncThunk } from '@store/redux';
import { AdcmConcernsApi, type RequestError } from '@api';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

const deleteClusterConcern = createAsyncThunk(
  'adcm/concerns/deleteClusterConcern',
  async (concernId: number, thunkAPI) => {
    try {
      await AdcmConcernsApi.deleteConcern(concernId);
      thunkAPI.dispatch(showInfo({ message: 'The concern has been deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

export { deleteClusterConcern };
