"""
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
  This file is part of the Smart Developer Hub Project:
    http://www.smartdeveloperhub.org

  Center for Open Middleware
        http://www.centeropenmiddleware.com/
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
  Copyright (C) 2015 Center for Open Middleware.
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

            http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
"""

import calendar
from sdh.metrics.server import MetricsApp
from sdh.metrics.org.store import ORGStore
from sdh.metrics.store.metrics import store_calc
import os
from urlparse import urlparse

__author__ = 'Alejandro F. Carrera'

config = os.environ.get('CONFIG', 'sdh.metrics.org.config.DevelopmentConfig')

app = MetricsApp(__name__, config)
st = ORGStore(**app.config['REDIS'])
app.store = st


#####################################


def transform_host_and_save_it(url):
    p = urlparse(url)
    p_host = p.scheme + '://' + p.netloc
    h = st.db.hexists('hosts', p_host)
    c = st.db.hget('hosts', 'cont')
    if c is None:
        st.db.hset('hosts', 'cont', 0)
        c = 0
    else:
        c = int(c)
    if not h:
        c += 1
        st.db.hset('hosts', p_host, c)
        st.db.hset('hosts', 'cont', c)
    return url.replace(p_host, str(c))


def get_last_path_from_url(url):
    return urlparse(url).path.split('/').pop(-1)


#####################################


@st.query([
    '?oh org:hasProduct ?prod',
    '?oh org:membership ?_mmb',
    '?_mmb org:member ?mem',
    '?mem org:id ?mid',
    '?_mmb org:position ?_pos',
    '?_pos rdfs:label ?pos',
])
def add_org_and_pos(arg):
    org = transform_host_and_save_it(arg.get('oh'))
    prod = transform_host_and_save_it(arg.get('prod'))
    mem = transform_host_and_save_it(arg.get('mem'))
    pos = str(arg.get('pos')).lower()
    st.execute('sadd', org + ':p:', prod)
    st.execute('sadd', org + ':m:' + pos, mem)
    st.execute('hset', mem, 'id', arg.get('mid'))


@st.query([
    '?prod org:relatesToProject ?prj',
    '?prj doap:repository ?rep',
    '?prj org:affiliation ?_aff',
    '?_aff org:affiliate ?mem'
])
def add_repositories_org(arg):
    prod = transform_host_and_save_it(arg.get("prod"))
    prj = transform_host_and_save_it(arg.get("prj"))
    mem = transform_host_and_save_it(arg.get('mem'))
    st.execute('sadd', prod + ':p:', prj)
    st.execute('sadd', prj + ':p:', prod)
    repo_name = get_last_path_from_url(arg.get('rep'))
    st.execute('hset', 'tmp-rep', repo_name, prj)
    old_proj = st.db.hget(mem, 'proj')
    if old_proj is None:
        st.execute('hset', mem, 'proj', [prj])
    else:
        old_proj = set(eval(old_proj))
        old_proj.add(prj)
        st.execute('hset', mem, 'proj', list(old_proj))

#####################################


@st.collect('?r scm:repositoryId ?rid')
def add_repository((r, _, rid)):
    repo_url = transform_host_and_save_it(r)
    st.execute('hset', repo_url, "id", rid.toPython())


@st.collect('?r doap:name ?name')
def add_repository_name((r, _, name)):
    repo_url = transform_host_and_save_it(r)
    prj = st.db.hget('tmp-rep', name.toPython())
    st.db.hdel('tmp-rep', name)
    st.execute('hset', repo_url, "name", name)
    st.execute('sadd', prj + ':r:', repo_url)


@st.collect('?r scm:firstCommit ?fc')
def add_repository_first_commit_info((r, _, fc)):
    repo_url = transform_host_and_save_it(r)
    timestamp = calendar.timegm(fc.toPython().timetuple())
    st.execute('zadd', 'frag:std-r-fc', timestamp, repo_url)
    st.execute('hset', repo_url, "first_commit", timestamp)


@st.collect('?r scm:lastCommit ?lc')
def add_repository_last_commit_info((r, _, lc)):
    repo_url = transform_host_and_save_it(r)
    timestamp = calendar.timegm(lc.toPython().timetuple())
    st.execute('zadd', 'frag:std-r-lc', timestamp, repo_url)
    st.execute('hset', repo_url, "last_commit", timestamp)
