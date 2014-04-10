from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from cacheops.conf import redis_client

KEYS = ['uncached', 'cached', 'invalidated']


@staff_member_required
@login_required
def cacheops_stats(request):
    if request.GET.get('reset'):
        redis_client.delete('stats_models')
        for key in redis_client.keys('cache_stats:*'):
            redis_client.delete(key)
        return redirect('cacheops_stats')

    data = {}
    graph_data = dict(zip(KEYS, [0, 0, 0]))
    for model in redis_client.smembers('stats_models'):
        total = dict(zip(KEYS[:2], [0, 0]))
        values = {}
        for i, k in enumerate(KEYS):
            d = redis_client.hgetall('cache_stats:%s:%d' % (model, i))
            if d:
                values[k] = d
                total[k] = sum(map(int, values[k].values()))
                graph_data[k] += total[k]

        total['total'] = sum(total.values())
        data[model] = {'data': values}
        data[model].update(total)

    graph_data['total'] = sum(graph_data.values())
    return render(request, 'cacheops/stats.html', {
        'data_list': data, 'graph_data': graph_data
    })
