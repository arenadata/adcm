import {
  createSlice,
  createAsyncThunk as createReduxAsyncThunk,
  AsyncThunkPayloadCreator,
  SliceCaseReducers,
  ValidateSliceCaseReducers,
  PayloadAction,
  ActionReducerMapBuilder,
  Draft,
} from '@reduxjs/toolkit';
import { StoreState, AppDispatch } from './store';
import { ListState, PaginationParams, SortParams } from '@models/table';

type ThunkApiConfig = { state: StoreState; dispatch: AppDispatch };

export function createAsyncThunk<Returned, ThunkArg = void>(
  typePrefix: string,
  payloadCreator: AsyncThunkPayloadCreator<Returned, ThunkArg, ThunkApiConfig>,
) {
  return createReduxAsyncThunk<Returned, ThunkArg>(typePrefix, payloadCreator);
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
type ExtractFilter<S> = S extends ListState<infer F, infer E> ? F : never;
// eslint-disable-next-line @typescript-eslint/no-unused-vars
type ExtractEntity<S> = S extends ListState<infer F, infer E> ? E : never;

type ExtractSortParams<S> = SortParams<ExtractEntity<S>>;

interface CreateListSliceOptions<
  S extends ListState<ExtractFilter<S>, ExtractEntity<S>>,
  CR extends SliceCaseReducers<S>,
  Name extends string = string,
> {
  name: Name;
  createInitialState: () => S;
  reducers: ValidateSliceCaseReducers<S, CR>;
  extraReducers?: (builder: ActionReducerMapBuilder<S>) => void;
}

export function createListSlice<
  S extends ListState<ExtractFilter<S>, ExtractEntity<S>>,
  CR extends SliceCaseReducers<S>,
>(options: CreateListSliceOptions<S, CR>) {
  const { name, createInitialState, reducers, extraReducers } = options;

  return createSlice({
    name,
    initialState: createInitialState(),
    reducers: {
      ...reducers,
      setFilter(state, action: PayloadAction<Partial<ExtractFilter<S>>>) {
        state.filter = {
          ...state.filter,
          ...action.payload,
        };
        state.paginationParams.pageNumber = 0;
      },
      resetFilter(state) {
        const initialData = createInitialState();
        state.filter = initialData.filter as Draft<ExtractFilter<S>>;
      },
      setPaginationParams(state, action: PayloadAction<PaginationParams>) {
        state.paginationParams = action.payload;
      },
      setSortParams(state, action: PayloadAction<ExtractSortParams<S>>) {
        state.sortParams = action.payload as Draft<ExtractSortParams<S>>;
      },
      resetSortParams(state) {
        state.sortParams = createInitialState().sortParams as Draft<ExtractSortParams<S>>;
      },
      setRequestFrequency(state, action: PayloadAction<number>) {
        state.requestFrequency = action.payload;
      },
      cleanupList() {
        return createInitialState();
      },
    },
    extraReducers,
  });
}
