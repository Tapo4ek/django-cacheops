# -*- coding: utf-8 -*-
from __future__ import absolute_import
import six
import redis
from funcy import memoize, merge
from functools import wraps
import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


CACHEOPS_REDIS = getattr(settings, 'CACHEOPS_REDIS', None)
CACHEOPS_DEFAULTS = getattr(settings, 'CACHEOPS_DEFAULTS', {})
CACHEOPS = getattr(settings, 'CACHEOPS', {})
CACHEOPS_LRU = getattr(settings, 'CACHEOPS_LRU', False)
CACHEOPS_DEGRADE_ON_FAILURE = getattr(settings, 'CACHEOPS_DEGRADE_ON_FAILURE', False)

FILE_CACHE_DIR = getattr(settings, 'FILE_CACHE_DIR', '/tmp/cacheops_file_cache')
FILE_CACHE_TIMEOUT = getattr(settings, 'FILE_CACHE_TIMEOUT', 60*60*24*30)

ALL_OPS = {'get', 'fetch', 'count', 'exists'}


# Support degradation on redis fail
DEGRADE_ON_FAILURE = getattr(settings, 'CACHEOPS_DEGRADE_ON_FAILURE', False)


def handle_connection_failure(func):
    if not DEGRADE_ON_FAILURE:
        return func

    @wraps(func)
    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.ConnectionError as e:
            warnings.warn("The cacheops cache is unreachable! Error: %s" % e, RuntimeWarning)

    return _inner

class SafeRedis(redis.StrictRedis):
    get = handle_connection_failure(redis.StrictRedis.get)


# Connecting to redis
try:
    redis_conf = settings.CACHEOPS_REDIS
except AttributeError:
    raise ImproperlyConfigured('You must specify non-empty CACHEOPS_REDIS setting to use cacheops')

redis_client = (SafeRedis if DEGRADE_ON_FAILURE else redis.StrictRedis)(**redis_conf)

@memoize
def prepare_profiles():
    """
    Prepares a dict 'app.model' -> profile, for use in model_profile()
    """
    profile_defaults = {
        'ops': (),
        'local_get': False,
        'db_agnostic': True,
    }
    profile_defaults.update(CACHEOPS_DEFAULTS)

    model_profiles = {}
    for app_model, profile in CACHEOPS.items():
        if profile is None:
            model_profiles[app_model] = None
            continue

        model_profiles[app_model] = mp = merge(profile_defaults, profile)
        if mp['ops'] == 'all':
            mp['ops'] = ALL_OPS
        # People will do that anyway :)
        if isinstance(mp['ops'], six.string_types):
            mp['ops'] = {mp['ops']}
        mp['ops'] = set(mp['ops'])

        if 'timeout' not in mp:
            raise ImproperlyConfigured(
                'You must specify "timeout" option in "%s" CACHEOPS profile' % app_model)

    return model_profiles

@memoize
def model_profile(model):
    """
    Returns cacheops profile for a model
    """
    model_profiles = prepare_profiles()

    app = model._meta.app_label
    model_name = model._meta.model_name
    for guess in ('%s.%s' % (app, model_name), '%s.*' % app, '*.*'):
        if guess in model_profiles:
            return model_profiles[guess]
    else:
        return None
