import {
  DEFAULT_ALLOWED_TAGS,
  escapeNonHtmlTags as escapeNonHtmlTagsUtil,
  sanitizeAllowedHtml,
} from '@utils/sanitizeUtils';

export const KNOWN_HTML_TAGS = [...DEFAULT_ALLOWED_TAGS];

export const escapeNonHtmlTags = (text: string): string => escapeNonHtmlTagsUtil(text, KNOWN_HTML_TAGS);

export const sanitizeErrorAlertHtml = (text: string): string =>
  sanitizeAllowedHtml(text, {
    allowedTags: KNOWN_HTML_TAGS,
    preserveUnknownTagsAsText: true,
  });
