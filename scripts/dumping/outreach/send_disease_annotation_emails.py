"""Send disease-annotation outreach emails to paper authors.

Joins the new-annotation TSV from extract_new_disease_annotations.py with
the email TSV from resolve_pmid_emails.py and sends one email per (PMID,
author email), telling the author their paper was used to annotate
disease at SGD and linking the paper page and each gene's disease tab.

Rules (per SGD curators, Oct 2026):
- weekly, for disease annotations added since the last run (the window
  is applied upstream by the extractor; initial batch since 2026-01-01)
- only papers with a PMID (any publication year)
- every send is appended to its own sent log, separate from the GO,
  phenotype and regulation campaigns'; a (pmid, email, gene) triple sent in
  production is never mentioned to that author again, so re-runs and
  overlapping windows are safe, and a paper that gains annotations on NEW genes in a later week
  gets one more email covering only those genes

Modes, sender, BCC-to-helpdesk, SMTP, NCBI esummary caching and the sent-log
format are shared with send_go_annotation_emails.py and
send_phenotype_annotation_emails.py (imported from them); the email layout
follows send_regulation_annotation_emails.py:
- default        dry run: write .txt/.html previews, no email, no log entries
- --test         send to --test-recipients ([TEST] subject + banner naming
                 the real recipient); logged mode=test, which does NOT block
                 a later production send
- --send         production send to the real authors, envelope-BCC'd to the
                 helpdesk list; logged mode=production
"""

import argparse
import html
import os
import time
from email.message import EmailMessage
from email.utils import formataddr

from send_go_annotation_emails import (
    DEFAULT_TEST_RECIPIENTS, HELPDESK_EMAIL, SENDER_EMAIL, SENDER_NAME,
    SGD_DOWNLOAD_URL, SGD_LOCUS_URL, SGD_REFERENCE_URL, SGD_SEARCH_URL,
    fetch_esummaries, format_citation, open_smtp)
from send_phenotype_annotation_emails import append_sent_log, load_sent_triples, read_tsv

# distinct from the GO, phenotype and regulation subjects so authors and the
# helpdesk can tell the datatypes apart
SUBJECT = 'Your publication has been used to annotate disease in SGD'
SGD_LOCUS_DISEASE_URL = 'https://www.yeastgenome.org/locus/{sgdid}/disease'
DISEASE_ONTOLOGY_URL = 'https://disease-ontology.org'

# disease annotations are manually curated, a handful per paper; the caps
# only guard against an unusually large paper, as in the phenotype emails
MAX_GENES_LISTED = 25
MAX_DISEASE_TAB_LINKS = 10


def parse_args():

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('-a', '--annotations', default='sgd_disease_new_annotations.tsv',
                        help='(pmid, gene) TSV from extract_new_disease_annotations.py')
    parser.add_argument('-e', '--emails', default='sgd_disease_emails.tsv',
                        help='email TSV from resolve_pmid_emails.py --pmid-file')
    parser.add_argument('-l', '--sent-log', default='sgd_disease_email_sent_log.tsv',
                        help='TSV log of what was already emailed; created if missing')
    parser.add_argument('-d', '--cache-dir', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'),
                        help='directory for cached NCBI esummary responses')
    parser.add_argument('--preview-dir', default='email_previews/disease',
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
    parser.add_argument('--bcc', default=HELPDESK_EMAIL,
                        help='comma-separated envelope BCC for every PRODUCTION send '
                             '(empty string disables; never applied to --test)')
    parser.add_argument('--smtp-host', default='localhost')
    parser.add_argument('--smtp-port', type=int, default=25)
    parser.add_argument('--smtp-user', default=os.environ.get('SMTP_USER'))
    parser.add_argument('--smtp-password', default=os.environ.get('SMTP_PASSWORD'))
    parser.add_argument('--sleep', type=float, default=1.0,
                        help='seconds to pause between SMTP sends')
    return parser.parse_args()


def read_papers(annotation_file, email_file, pmid_filter):
    """Return {pmid: {'emails': set, 'genes': {sgdid: symbol}, 'annotations': int}}
    for papers that have both new annotations and at least one author email."""

    emails_by_pmid = {}
    for row in read_tsv(email_file):
        emails = [e.strip().lower() for e in row['email'].split('|') if e.strip()]
        emails_by_pmid.setdefault(row['pmid'], set()).update(emails)

    papers = {}
    for row in read_tsv(annotation_file):
        pmid = row['pmid']
        if not pmid.isdigit() or pmid not in emails_by_pmid:
            continue
        if pmid_filter and pmid not in pmid_filter:
            continue
        paper = papers.setdefault(pmid, {'emails': emails_by_pmid[pmid], 'genes': {},
                                         'annotations': int(row['paper_annotation_count'])})
        paper['genes'][row['gene_sgdid']] = row['gene_symbol'] or row['gene_sgdid']
    return papers


def build_bodies(citation, genes, annotation_count, pmid):
    """Return (plain_text, html_body). genes is {sgdid: symbol}, listed by name."""

    ordered = sorted(genes.items(), key=lambda item: item[1])
    listed = ordered[:MAX_GENES_LISTED]
    tab_linked = ordered[:MAX_DISEASE_TAB_LINKS]
    unlisted = len(ordered) - len(listed)
    unlinked = len(ordered) - len(tab_linked)
    paper_url = SGD_REFERENCE_URL.format(pmid=pmid)
    annotation_sentence = ('These annotations are now part of SGD, will be distributed through our pages and'
                           if annotation_count > 1 else
                           'This annotation is now part of SGD, will be distributed through our pages and')

    gene_links_html = ', '.join('<a href="' + SGD_LOCUS_URL.format(sgdid=sgdid) + '">'
                                + html.escape(symbol) + '</a>' for sgdid, symbol in listed)
    gene_names_text = ', '.join(symbol for _, symbol in listed)
    if unlisted:
        gene_links_html += ' and {:,} more'.format(unlisted)
        gene_names_text += ' and {:,} more'.format(unlisted)

    tab_lines_html = '\n\n'.join('<p><a href="' + SGD_LOCUS_DISEASE_URL.format(sgdid=sgdid) + '">'
                                 + html.escape(symbol) + ' disease</a></p>'
                                 for sgdid, symbol in tab_linked)
    tab_lines_text = '\n\n'.join(symbol + ' disease: ' + SGD_LOCUS_DISEASE_URL.format(sgdid=sgdid)
                                 for sgdid, symbol in tab_linked)
    if unlinked:
        tab_lines_html += ('\n\n<p>Disease annotations for the other {:,} genes are listed on '
                           '<a href="{}">your paper\'s page</a> at SGD.</p>').format(unlinked, paper_url)
        tab_lines_text += ('\n\nDisease annotations for the other {:,} genes are listed on '
                           'your paper\'s page at SGD ({}).').format(unlinked, paper_url)

    html_body = """\
<p>Hello,</p>

<p>Great news! Your publication has been used to annotate disease in the
<i>Saccharomyces</i> Genome Database (<a href="{sgd_home}">SGD</a>):</p>

<p>{citation}</p>

<p>Genes: {gene_links}</p>

<p>View your contribution:</p>

<p><a href="{paper_url}">Your paper at SGD</a></p>

{tab_lines}

<p>Your findings were captured using <a href="{do_url}">Disease Ontology (DO)</a> terms,
making your research more discoverable to scientists worldwide and enabling computational analyses
across organisms.</p>

<p>{annotation_sentence} will also be shared via
<a href="{download}">download files</a>.</p>

<p>Questions? Contact us at <a href="mailto:{helpdesk}">{helpdesk}</a>.</p>

<p>Best regards,</p>

<p>The SGD Team</p>
""".format(sgd_home=SGD_SEARCH_URL, citation=html.escape(citation), gene_links=gene_links_html,
           paper_url=paper_url, tab_lines=tab_lines_html, annotation_sentence=annotation_sentence,
           do_url=DISEASE_ONTOLOGY_URL, download=SGD_DOWNLOAD_URL, helpdesk=HELPDESK_EMAIL)

    plain_text = """\
Hello,

Great news! Your publication has been used to annotate disease in the
Saccharomyces Genome Database (SGD, {sgd_home}):

{citation}

Genes: {gene_names}

View your contribution:

Your paper at SGD: {paper_url}

{tab_lines}

Your findings were captured using Disease Ontology (DO, {do_url}) terms,
making your research more discoverable to scientists worldwide and enabling
computational analyses across organisms.

{annotation_sentence}
will also be shared via download files ({download}).

Questions? Contact us at {helpdesk}.

Best regards,

The SGD Team
""".format(sgd_home=SGD_SEARCH_URL, citation=citation, gene_names=gene_names_text,
           paper_url=paper_url, tab_lines=tab_lines_text, annotation_sentence=annotation_sentence,
           do_url=DISEASE_ONTOLOGY_URL, download=SGD_DOWNLOAD_URL, helpdesk=HELPDESK_EMAIL)

    # Outlook desktop and Mac Mail collapse default <p> margins in HTML
    # email, so paragraph spacing must be declared inline on every <p>
    html_body = html_body.replace('<p>', '<p style="margin:0 0 1em 0;">')
    html_body = '<html><body>\n' + html_body + '</body></html>\n'

    return plain_text, html_body


def main():

    args = parse_args()
    mode = 'production' if args.send else 'test' if args.test else 'dry-run'
    limit = args.limit
    if limit is None and mode == 'test':
        limit = 5

    papers = read_papers(args.annotations, args.emails, set(args.pmid or []))
    docs = fetch_esummaries(sorted(papers), args.cache_dir)
    sent_triples = load_sent_triples(args.sent_log)
    test_recipients = [r.strip() for r in args.test_recipients.split(',') if r.strip()]
    bcc = [a.strip() for a in args.bcc.split(',') if a.strip()] if mode == 'production' else []

    # one message per (pmid, email), covering only the genes not yet
    # mentioned to that author for that paper
    queue = []
    skipped = 0
    for pmid in sorted(papers):
        if pmid not in docs:
            continue
        for email in sorted(papers[pmid]['emails']):
            genes = {sgdid: symbol for sgdid, symbol in papers[pmid]['genes'].items()
                     if (pmid, email, sgdid) not in sent_triples}
            if not genes:
                skipped += 1
                continue
            queue.append((pmid, email, genes))
    if limit is not None:
        queue = queue[:limit]

    print('mode={} papers_with_emails={} messages_queued={} already_sent_skipped={}'.format(
        mode, len(papers), len(queue), skipped))

    smtp = None
    if mode != 'dry-run':
        smtp = open_smtp(args)
    else:
        os.makedirs(args.preview_dir, exist_ok=True)

    for pmid, email, genes in queue:
        citation = format_citation(docs[pmid])
        plain_text, html_body = build_bodies(citation, genes, papers[pmid]['annotations'], pmid)
        subject = SUBJECT
        gene_summary = ', '.join(sorted(genes.values())[:5]) + (' ...' if len(genes) > 5 else '')

        if mode == 'dry-run':
            base = os.path.join(args.preview_dir, pmid + '_' + email.replace('@', '_at_'))
            with open(base + '.txt', 'w') as fh:
                fh.write('Subject: ' + subject + '\nTo: ' + email + '\n\n' + plain_text)
            with open(base + '.html', 'w') as fh:
                fh.write(html_body)
            print('preview: {} -> {} ({} genes: {})'.format(pmid, email, len(genes), gene_summary))
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
        smtp.send_message(message, from_addr=args.from_email, to_addrs=recipients + bcc)
        append_sent_log(args.sent_log, mode, pmid, email, genes, ','.join(recipients + bcc))
        print('sent ({}): {} -> {} ({} genes)'.format(mode, pmid, ','.join(recipients + bcc), len(genes)))
        time.sleep(args.sleep)

    if smtp:
        smtp.quit()


if __name__ == '__main__':
    main()
