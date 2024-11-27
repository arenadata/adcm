const lintCheck = (filenames) => {
  const preparedFilenames = filenames.join(' ');
  return `yarn biome-check --staged && yarn oxlint-check ${preparedFilenames}`;
}

export default {
  '*.(js|jsx|ts|tsx)': async (filenames) => {
    // Run the whole check
    if (filenames.length > 10) {
      return 'yarn lint';
    }

    return lintCheck(filenames);
  },
};
