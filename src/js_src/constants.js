export const SEARCH_API_ERROR_MESSAGE = 'There was a problem connecting to the server. Please refresh the page.  If you continue to see this message, please contact sgd-programmers@lists.stanford.edu';
export const LARGE_COL_CLASS = 'columns small-8 medium-9';
export const NON_HIGHLIGHTED_FIELDS = ['sourceHref', 'href', 'category', 'homologs', 'paralogs', 'orthologs', 'homologs.symbol', 'homologs.panther_family'];
export const SMALL_COL_CLASS = 'columns small-4 medium-3';
let URL = process.env.PREVIEW_URL;
if (URL != 'https://preview.qa.yeastgenome.org') {
  URL = 'https://preview.yeastgenome.org';
}
export const PREVIEW_URL = URL;
export const ml_12 = {marginLeft:'12px'};
