# src/stats.py

import psutil
import time
from urllib.parse import urlencode
from sqlalchemy import event
from sqlalchemy.engine import Engine
from pyramid.tweens import INGRESS
import os
import logging

from .util import get_root_request  # Correct relative import


# Initialize the logger for this module
logger = logging.getLogger('src.stats')


def includeme(config):
    """
    Pyramid includeme hook to add the stats tween.
    """
    config.add_tween('src.stats.stats_tween_factory', under=INGRESS)


def requests_timing_hook(prefix='requests'):
    """
    Hook to measure external HTTP requests timing.
    """
    count_key = f'{prefix}_count'
    time_key = f'{prefix}_time'

    def response_hook(r, *args, **kwargs):
        request = get_root_request()
        if request is None:
            return

        # Initialize stats if not present
        if not hasattr(request, '_stats'):
            request._stats = {}
        stats = request._stats

        stats[count_key] = stats.get(count_key, 0) + 1

        # Convert timedelta to microseconds
        if hasattr(r, 'elapsed') and r.elapsed:
            e = r.elapsed
            duration = (e.days * 86400 + e.seconds) * 1_000_000 + e.microseconds
            stats[time_key] = stats.get(time_key, 0) + duration

    return response_hook


# SQLAlchemy Event Listeners for Profiling
@event.listens_for(Engine, 'before_cursor_execute')
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = int(time.time() * 1e6)


@event.listens_for(Engine, 'after_cursor_execute')
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    end = int(time.time() * 1e6)

    request = get_root_request()
    if request is None:
        return

    # Initialize stats if not present
    if not hasattr(request, '_stats'):
        request._stats = {}
    stats = request._stats

    stats['db_count'] = stats.get('db_count', 0) + 1
    duration = end - context._query_start_time
    stats['db_time'] = stats.get('db_time', 0) + duration


def stats_tween_factory(handler, registry):
    """
    Pyramid tween factory to collect stats for each request.
    """
    process = psutil.Process()
    enable_stats = os.environ.get('ENABLE_STATS', 'false').lower() == 'true'

    def stats_tween(request):
        # Initialize stats dictionary
        request._stats = {}
        stats = request._stats

        # Memory usage before processing the request
        rss_begin = process.memory_info().rss
        stats['rss_begin'] = rss_begin

        # Start time in microseconds
        begin = int(time.time() * 1e6)
        stats['wsgi_begin'] = begin

        # Handle the request and get the response
        response = handler(request)

        # End time in microseconds
        end = int(time.time() * 1e6)
        stats['wsgi_end'] = end

        # Memory usage after processing the request
        rss_end = process.memory_info().rss
        stats['rss_end'] = rss_end
        stats['rss_change'] = rss_end - rss_begin

        # Calculate WSGI processing time
        stats['wsgi_time'] = end - begin

        # Optional: Calculate queue time if available (specific to mod_wsgi)
        environ = request.environ
        if 'mod_wsgi.queue_start' in environ:
            try:
                queue_begin = int(environ['mod_wsgi.queue_start'])
                stats['queue_begin'] = queue_begin
                stats['queue_time'] = begin - queue_begin
            except ValueError:
                # Handle cases where the environment variable isn't an integer
                stats['queue_begin'] = None
                stats['queue_time'] = None

        # Conditionally add X-Stats header based on environment variable
        if enable_stats:
            # Encode stats into a query string format
            xs = urlencode(sorted(stats.items()))
            response.headers['X-Stats'] = xs

            # Optional: Set a cookie with the stats if required
            if getattr(request, '_stats_html_attribute', False):
                response.set_cookie('X-Stats', xs)

            # Log the stats for persistent storage
            logger.info(f"Request {request.method} {request.path}: {stats}")

        return response

    return stats_tween
