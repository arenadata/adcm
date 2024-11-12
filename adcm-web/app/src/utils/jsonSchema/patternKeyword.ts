/* eslint-disable spellcheck/spell-checker */
/* 
   Custom pattern keyword definition. 
   Based on https://github.com/ajv-validator/ajv/blob/master/lib/vocabularies/validation/pattern.ts
*/

import type { CodeKeywordDefinition, KeywordCxt, KeywordErrorDefinition } from 'ajv/dist/2020';
import { _ } from 'ajv/dist/2020';
import type { KeywordErrorCxt } from 'ajv/dist/types';
import { usePattern as generatePattern } from 'ajv/dist/vocabularies/code';

const error: KeywordErrorDefinition = {
  message: (ctx: KeywordErrorCxt) => {
    const isPatternValid = (ctx as SafePatternKeywordCtx).isPatternValid;
    return isPatternValid ? `must match pattern ${ctx.schemaCode}` : `invalid pattern ${ctx.schemaCode}`;
  },
  params: (ctx: KeywordErrorCxt) => {
    return _`{pattern: ${ctx.schemaCode}}`;
  },
};

type SafePatternKeywordCtx = KeywordCxt & {
  isPatternValid: boolean;
};

export const safePattern: CodeKeywordDefinition = {
  keyword: 'pattern',
  type: 'string',
  schemaType: 'string',
  $data: true,
  error,
  code(cxt: KeywordCxt) {
    const { data, $data, schema, schemaCode, it } = cxt;
    const u = it.opts.unicodeRegExp ? 'u' : '';
    try {
      const regExp = $data ? _`(new RegExp(${schemaCode}, ${u}))` : generatePattern(cxt, schema);
      (cxt as SafePatternKeywordCtx).isPatternValid = true;
      cxt.fail$data(_`!${regExp}.test(${data})`);
    } catch (_e) {
      (cxt as SafePatternKeywordCtx).isPatternValid = false;
      cxt.fail();
    }
  },
};
