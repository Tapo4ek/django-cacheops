try:
    from django.conf.urls import patterns, include, url
except:
    from django.conf.urls.defaults import patterns, include, url

from cacheops.views import cacheops_stats

urlpatterns = patterns(
    '',
    url('^cacheops/stats/$', cacheops_stats, name='cacheops_stats'),
)
