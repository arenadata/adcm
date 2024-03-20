import { LoadState } from '@models/loadState';

export const isShowSpinner = (loadState: LoadState): loadState is LoadState.Loading | LoadState.NotLoaded =>
  loadState === LoadState.Loading || loadState === LoadState.NotLoaded;
