import { ModalState } from '@models/modal';
import { ActionReducerMapBuilder, SliceCaseReducers, ValidateSliceCaseReducers, createSlice } from '@reduxjs/toolkit';

type ExtractEntity<S> = S extends ModalState<infer E, string> ? E : never;

interface CreateCrudSliceOptions<
  EntityName extends string,
  S extends ModalState<ExtractEntity<S>, EntityName>,
  CR extends SliceCaseReducers<S>,
  Name extends string = string,
> {
  name: Name;
  entityName: EntityName;
  createInitialState: () => S;
  reducers: ValidateSliceCaseReducers<S, CR>;
  extraReducers?: (builder: ActionReducerMapBuilder<S>) => void;
}

export function createCrudSlice<
  EntityName extends string,
  S extends ModalState<ExtractEntity<S>, string>,
  CR extends SliceCaseReducers<S>,
>(options: CreateCrudSliceOptions<EntityName, S, CR>) {
  const { name, entityName, createInitialState, reducers, extraReducers } = options;

  return createSlice({
    name,
    initialState: createInitialState,
    reducers: {
      ...reducers,
      setIsActionInProgress(state, action) {
        state.isActionInProgress = action.payload;
      },
      openCreateDialog(state) {
        state.createDialog.isOpen = true;
      },
      openUpdateDialog(state, action) {
        state.updateDialog[entityName] = action.payload;
      },
      openDeleteDialog(state, action) {
        state.deleteDialog[entityName] = action.payload;
      },
      closeCreateDialog(state) {
        state.createDialog.isOpen = false;
      },
      closeUpdateDialog(state) {
        state.updateDialog[entityName] = null;
      },
      closeDeleteDialog(state) {
        state.deleteDialog[entityName] = null;
      },
      cleanupActions() {
        return createInitialState();
      },
    },
    extraReducers,
  });
}
