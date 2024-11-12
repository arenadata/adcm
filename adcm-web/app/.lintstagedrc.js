import { ESLint } from 'eslint';

const eslintCheck = (filenames) => `eslint ${filenames.join(' ')} --report-unused-disable-directives --max-warnings 0`;

/**
 * lint-stage don't understand .eslintignore file
 * https://www.curiouslychase.com/posts/eslint-error-file-ignored-because-of-a-matching-ignore-pattern/
 */
const removeIgnoredFiles = async (files) => {
  const eslint = new ESLint();
  const isIgnored = await Promise.all(
    files.map((file) => {
      return eslint.isPathIgnored(file);
    }),
  );
  return files.filter((_, i) => !isIgnored[i]);
};

export default {
  '*.(js|jsx|ts|tsx)': async (filenames) => {
    // Run ESLint on entire repo if more than 10 staged files
    if (filenames.length > 10) {
      return 'yarn lint';
    }
    const filesToLint = await removeIgnoredFiles(filenames);
    return eslintCheck(filesToLint);
  },
};
