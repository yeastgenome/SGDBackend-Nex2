"""Send GO-annotation outreach emails to paper authors.

Reads the gene-centric email/annotation TSV produced by
map_emails_to_go_annotations.py and sends one email per (PMID, author email)
pair, telling the author their paper was used for GO annotation at SGD.

Rules (per SGD curators, Aug 2026):
- only annotations with annotation_date >= --since (initial batch: 2026-01-01)
- only papers with a numeric PMID (no GO_REFs)
- every send is appended to a sent-log TSV; (pmid, email) pairs already sent
  in production mode are skipped on later runs, so the script can be re-run
  after every GO release with a widened --since window.

Modes:
- default        dry run: write .txt/.html previews, no email, no log entries
- --test         send via SMTP to --test-recipients instead of the authors
                 (subject gets a [TEST] prefix, body gets a banner with the
                 real recipient); logged with mode=test, which does NOT block
                 a later production send
- --send         production send to the real author emails; logged with
                 mode=production

Citations and author names come from NCBI esummary (batched, cached as one
JSON file per PMID under --cache-dir). Requires network for uncached PMIDs.

Example (initial batch, dry run):
    python3 send_go_annotation_emails.py \
        -i sgd_email_pmid_go_annotations_gene_centric.tsv --since 2026-01-01
"""

import argparse
import html
import json
import os
import smtplib
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr

# sgd-curate's postfix relays via AWS SES, which only accepts SES-verified
# sender identities; the yeastgenome.org domain is verified in the agr-sgd
# account, so the From must stay on that domain — replies and the body's
# contact line still point at the Stanford helpdesk list
HELPDESK_EMAIL = 'sgd-helpdesk@lists.stanford.edu'
SENDER_EMAIL = 'sgd-helpdesk@yeastgenome.org'
SENDER_NAME = 'The SGD Team'
SUBJECT = 'Your publication is now part of the Saccharomyces Genome Database (SGD)'
DEFAULT_TEST_RECIPIENTS = 'sweng@stanford.edu,wengshuai@gmail.com'

SGD_SEARCH_URL = 'https://www.yeastgenome.org/search'
SGD_REFERENCE_URL = 'https://www.yeastgenome.org/reference/{pmid}'
SGD_LOCUS_URL = 'https://www.yeastgenome.org/locus/{sgdid}'
SGD_LOCUS_GO_URL = 'https://www.yeastgenome.org/locus/{sgdid}/go'
SGD_DOWNLOAD_URL = 'http://sgd-archive.yeastgenome.org/curation/literature/'
GO_HELP_URL = 'https://geneontology.org/docs/go-annotations/'
GO_HOME_URL = 'https://geneontology.org/'

ESUMMARY_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
ESUMMARY_BATCH_SIZE = 100
NCBI_SLEEP = 0.35

SENT_LOG_COLUMNS = ['sent_at', 'mode', 'pmid', 'email', 'genes', 'delivered_to']


def parse_args():

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('-i', '--input', default='sgd_email_pmid_go_annotations_gene_centric.tsv',
                        help='gene-centric email/annotation TSV from map_emails_to_go_annotations.py')
    parser.add_argument('--since', default='2026-01-01',
                        help='only include annotations with annotation_date >= this (YYYY-MM-DD)')
    parser.add_argument('-l', '--sent-log', default='sgd_go_email_sent_log.tsv',
                        help='TSV log of (pmid, email) pairs already emailed; created if missing')
    parser.add_argument('-d', '--cache-dir', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'),
                        help='directory for cached NCBI esummary responses')
    parser.add_argument('--preview-dir', default='email_previews',
                        help='dry-run mode: directory for .txt/.html previews')
    parser.add_argument('--pmid', action='append', default=None,
                        help='restrict to specific PMID(s); repeatable')
    parser.add_argument('--limit', type=int, default=None,
                        help='send/preview at most N messages (default 5 in --test mode)')

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--test', action='store_true',
                      help='send to --test-recipients instead of authors')
    mode.add_argument('--send', action='store_true',
                      help='PRODUCTION: send to the real author emails')

    parser.add_argument('--test-recipients', default=DEFAULT_TEST_RECIPIENTS,
                        help='comma-separated recipients for --test mode')
    parser.add_argument('--from-email', default=SENDER_EMAIL,
                        help='override the SMTP From address (must be SES-verified)')
    parser.add_argument('--smtp-host', default='localhost')
    parser.add_argument('--smtp-port', type=int, default=25)
    parser.add_argument('--smtp-user', default=os.environ.get('SMTP_USER'))
    parser.add_argument('--smtp-password', default=os.environ.get('SMTP_PASSWORD'))
    parser.add_argument('--sleep', type=float, default=1.0,
                        help='seconds to pause between SMTP sends')
    return parser.parse_args()


def read_annotations(input_file, since, pmid_filter):
    """Group qualifying TSV rows into one record per (pmid, email)."""

    papers = {}
    with open(input_file) as fh:
        header = fh.readline().rstrip('\n').split('\t')
        col = {name: idx for idx, name in enumerate(header)}
        for line in fh:
            row = line.rstrip('\n').split('\t')
            pmid = row[col['pmid']].strip()
            if not pmid.isdigit():
                continue
            if pmid_filter and pmid not in pmid_filter:
                continue
            if row[col['annotation_date']] < since:
                continue
            if row[col['assigned_by']] != 'SGD':
                continue
            emails = [e.strip() for e in row[col['emails']].split('|') if e.strip()]
            if not emails:
                continue
            paper = papers.setdefault(pmid, {'emails': set(), 'genes': {}})
            paper['emails'].update(emails)
            sgdid = row[col['gene_sgdid']].replace('SGD:', '')
            paper['genes'][sgdid] = row[col['gene_symbol']] or sgdid
    return papers


def fetch_esummaries(pmids, cache_dir):
    """Return {pmid: esummary doc}; batch-fetch anything not in cache_dir."""

    os.makedirs(cache_dir, exist_ok=True)
    docs = {}
    missing = []
    for pmid in pmids:
        cache_file = os.path.join(cache_dir, 'esummary_' + pmid + '.json')
        if os.path.exists(cache_file):
            with open(cache_file) as fh:
                docs[pmid] = json.load(fh)
        else:
            missing.append(pmid)

    api_key = os.environ.get('NCBI_API_KEY')
    for start in range(0, len(missing), ESUMMARY_BATCH_SIZE):
        chunk = missing[start:start + ESUMMARY_BATCH_SIZE]
        params = {'db': 'pubmed', 'id': ','.join(chunk), 'retmode': 'json'}
        if api_key:
            params['api_key'] = api_key
        url = ESUMMARY_URL + '?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url) as response:
            result = json.load(response).get('result', {})
        for pmid in chunk:
            doc = result.get(pmid)
            if not doc or doc.get('error'):
                print('WARNING: no esummary for PMID ' + pmid, file=sys.stderr)
                continue
            docs[pmid] = doc
            cache_file = os.path.join(cache_dir, 'esummary_' + pmid + '.json')
            with open(cache_file, 'w') as fh:
                json.dump(doc, fh)
        time.sleep(NCBI_SLEEP)
    return docs


def format_citation(doc):

    authors = [a['name'] for a in doc.get('authors', []) if a.get('name')]
    if len(authors) > 2:
        author_str = authors[0] + ', et al.'
    elif authors:
        author_str = ' and '.join(authors)
    else:
        author_str = '[no authors listed]'

    year = (doc.get('pubdate') or '')[:4]
    title = (doc.get('title') or '').strip()
    citation = author_str + ' (' + year + ') ' + title
    journal_part = doc.get('source') or ''
    if doc.get('volume'):
        journal_part += ' ' + doc['volume']
        if doc.get('issue'):
            journal_part += '(' + doc['issue'] + ')'
        if doc.get('pages'):
            journal_part += ':' + doc['pages']
    if journal_part:
        citation += ' ' + journal_part.strip()
    return citation.strip()


def build_bodies(citation, genes, pmid):
    """Return (plain_text, html_body). genes is {sgdid: symbol}."""

    salutation = 'Hello,'
    ordered = sorted(genes.items(), key=lambda item: item[1])
    plural = len(ordered) > 1
    annotation_sentence = ('These annotations are now part of SGD, will be distributed through our pages and'
                           if plural else
                           'This annotation is now part of SGD, will be distributed through our pages and')

    paper_url = SGD_REFERENCE_URL.format(pmid=pmid)
    gene_links_html = ', '.join('<a href="' + SGD_LOCUS_URL.format(sgdid=sgdid) + '">'
                                + html.escape(symbol) + '</a>'
                                for sgdid, symbol in ordered)
    go_tab_lines_html = '\n\n'.join('<p><a href="' + SGD_LOCUS_GO_URL.format(sgdid=sgdid) + '">'
                                    + html.escape(symbol) + ' GO annotations</a></p>'
                                    for sgdid, symbol in ordered)

    html_body = """\
<p>{salutation}</p>

<p>Great news! Your publication has been used to annotate gene function in the
<i>Saccharomyces</i> Genome Database (<a href="{sgd_home}">SGD</a>):</p>

<p>{citation}</p>

<p>Genes: {gene_links}</p>

<p>View your contribution:</p>

<p><a href="{paper_url}">Your paper at SGD</a></p>

{go_tab_lines}

<p>Your findings were captured using <a href="{go_help}">Gene Ontology (GO)</a> terms,
making your research more discoverable to scientists worldwide and enabling
computational analyses across organisms.</p>

<p>{annotation_sentence} <a href="{download}">download files</a>, and will also be
shared via the <a href="{go_home}">Gene Ontology Resource</a>.</p>

<p>Questions or comments? Contact us at
<a href="mailto:{helpdesk}">{helpdesk}</a>.</p>

<p>Best regards,</p>

<p>The SGD Team</p>
""".format(salutation=html.escape(salutation), sgd_home=SGD_SEARCH_URL,
           citation=html.escape(citation), gene_links=gene_links_html,
           paper_url=paper_url, go_tab_lines=go_tab_lines_html,
           go_help=GO_HELP_URL, annotation_sentence=annotation_sentence,
           download=SGD_DOWNLOAD_URL, go_home=GO_HOME_URL, helpdesk=HELPDESK_EMAIL)

    gene_names = ', '.join(symbol for _, symbol in ordered)
    go_tab_lines_text = '\n\n'.join(symbol + ' GO annotations: ' + SGD_LOCUS_GO_URL.format(sgdid=sgdid)
                                    for sgdid, symbol in ordered)
    plain_text = """\
{salutation}

Great news! Your publication has been used to annotate gene function in the
Saccharomyces Genome Database (SGD, {sgd_home}):

{citation}

Genes: {gene_names}

View your contribution:

Your paper at SGD: {paper_url}

{go_tab_lines}

Your findings were captured using Gene Ontology (GO) terms
({go_help}), making your research more
discoverable to scientists worldwide and enabling computational analyses
across organisms.

{annotation_sentence} download files
({download}), and will also be
shared via the Gene Ontology Resource ({go_home}).

Questions or comments? Contact us at {helpdesk}.

Best regards,

The SGD Team
""".format(salutation=salutation, sgd_home=SGD_SEARCH_URL, citation=citation,
           gene_names=gene_names, paper_url=paper_url,
           go_tab_lines=go_tab_lines_text, go_help=GO_HELP_URL,
           annotation_sentence=annotation_sentence, download=SGD_DOWNLOAD_URL,
           go_home=GO_HOME_URL, helpdesk=HELPDESK_EMAIL)

    # Outlook desktop and Mac Mail collapse default <p> margins in HTML
    # email, so paragraph spacing must be declared inline on every <p>
    html_body = html_body.replace('<p>', '<p style="margin:0 0 1em 0;">')
    html_body = '<html><body>\n' + html_body + '</body></html>\n'

    return plain_text, html_body


def load_sent_pairs(sent_log):
    """Return the set of (pmid, email) pairs already sent in production mode."""

    sent = set()
    if not os.path.exists(sent_log):
        return sent
    with open(sent_log) as fh:
        header = fh.readline().rstrip('\n').split('\t')
        col = {name: idx for idx, name in enumerate(header)}
        for line in fh:
            row = line.rstrip('\n').split('\t')
            if row[col['mode']] == 'production':
                sent.add((row[col['pmid']], row[col['email']].lower()))
    return sent


def append_sent_log(sent_log, mode, pmid, email, genes, delivered_to):

    is_new = not os.path.exists(sent_log)
    with open(sent_log, 'a') as fh:
        if is_new:
            fh.write('\t'.join(SENT_LOG_COLUMNS) + '\n')
        sent_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        gene_names = ','.join(sorted(genes.values()))
        fh.write('\t'.join([sent_at, mode, pmid, email, gene_names, delivered_to]) + '\n')


def open_smtp(args):

    smtp = smtplib.SMTP(args.smtp_host, args.smtp_port, timeout=30)
    if args.smtp_user and args.smtp_password:
        smtp.starttls()
        smtp.login(args.smtp_user, args.smtp_password)
    return smtp


def main():

    args = parse_args()
    mode = 'production' if args.send else 'test' if args.test else 'dry-run'
    limit = args.limit
    if limit is None and mode == 'test':
        limit = 5

    papers = read_annotations(args.input, args.since, set(args.pmid or []))
    docs = fetch_esummaries(sorted(papers), args.cache_dir)
    sent_pairs = load_sent_pairs(args.sent_log)
    test_recipients = [r.strip() for r in args.test_recipients.split(',') if r.strip()]

    queue = []
    skipped = 0
    for pmid in sorted(papers):
        if pmid not in docs:
            continue
        for email in sorted(papers[pmid]['emails']):
            if (pmid, email.lower()) in sent_pairs:
                skipped += 1
                continue
            queue.append((pmid, email))
    if limit is not None:
        queue = queue[:limit]

    print('mode={} papers={} messages_queued={} already_sent_skipped={}'.format(
        mode, len(papers), len(queue), skipped))

    smtp = None
    if mode != 'dry-run':
        smtp = open_smtp(args)
    else:
        os.makedirs(args.preview_dir, exist_ok=True)

    for pmid, email in queue:
        doc = docs[pmid]
        genes = papers[pmid]['genes']
        citation = format_citation(doc)
        plain_text, html_body = build_bodies(citation, genes, pmid)
        subject = SUBJECT

        if mode == 'dry-run':
            base = os.path.join(args.preview_dir, pmid + '_' + email.replace('@', '_at_'))
            with open(base + '.txt', 'w') as fh:
                fh.write('Subject: ' + subject + '\nTo: ' + email + '\n\n' + plain_text)
            with open(base + '.html', 'w') as fh:
                fh.write(html_body)
            print('preview: {} -> {} ({})'.format(pmid, email, ', '.join(sorted(genes.values()))))
            continue

        recipients = [email]
        if mode == 'test':
            recipients = test_recipients
            subject = '[TEST] ' + subject
            banner = '[TEST MESSAGE — in production this would go to: ' + email + ']'
            plain_text = banner + '\n\n' + plain_text
            banner_html = '<p style="margin:0 0 1em 0;"><b>' + html.escape(banner) + '</b></p>\n'
            html_body = html_body.replace('<html><body>\n', '<html><body>\n' + banner_html, 1)

        message = EmailMessage()
        message['From'] = formataddr((SENDER_NAME, args.from_email))
        message['Reply-To'] = HELPDESK_EMAIL
        message['To'] = ', '.join(recipients)
        message['Subject'] = subject
        message.set_content(plain_text)
        message.add_alternative(html_body, subtype='html')
        smtp.send_message(message, from_addr=args.from_email, to_addrs=recipients)
        append_sent_log(args.sent_log, mode, pmid, email, genes, ','.join(recipients))
        print('sent ({}): {} -> {}'.format(mode, pmid, ','.join(recipients)))
        time.sleep(args.sleep)

    if smtp:
        smtp.quit()


if __name__ == '__main__':
    main()
