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


def remove_and_clean_string(string):
    dw = " ".join(string.split())
    dw = dw.replace(" ", "")
    return dw.lower()


#####################################


@st.query([
    '?oh org:hasProduct ?prod',
    '?prod org:id ?prid',
    '?oh org:membership ?_mmb',
    '?_mmb org:member ?mem',
    '?mem org:id ?mid',
    '?_mmb org:position ?_pos',
    '?_pos rdfs:label ?pos'
])
def add_org_and_pos(arg):
    org = arg.get('oh')
    prod = arg.get('prod')
    mem = arg.get('mem')
    prid = arg.get('prid')
    pos = remove_and_clean_string(arg.get('pos'))
    st.execute('sadd', org + ':p:', prod)
    st.execute('sadd', org + ':m:' + pos, mem)
    st.execute('hset', mem, 'id', arg.get('mid'))
    st.execute('set', prod, prid)


@st.query([
    '?oh org:hasProduct ?prod',
    '?prod org:relatesToProject ?prj',
    '?prod org:id ?prid',
    '?prj org:id ?prjid',
    '?prj doap:repository ?rep',
    '?prj org:affiliation ?_aff',
    '?_aff org:affiliate ?mem',
    '?_aff org:role ?_role',
    '?_role rdfs:label ?rol'
])
def add_repositories_org(arg):
    org = arg.get('oh')
    prod = arg.get("prod")
    prj = arg.get("prj")
    mem = arg.get('mem')
    prid = arg.get('prid')
    prjid = arg.get('prjid')
    role = remove_and_clean_string(arg.get('rol'))
    st.execute('set', prj, prjid)
    st.execute('set', prod, prid)
    st.execute('sadd', org + ':m:' + role, mem)
    st.execute('sadd', prod + ':pj:', prj)
    st.execute('sadd', prj + ':p:', prod)
    repo_name = get_last_path_from_url(arg.get('rep'))
    st.execute('hset', 'tmp-rep', repo_name, prj)
    old_proj = st.db.hget(mem, 'proj')
    if old_proj is None:
        st.execute('hset', mem, 'proj', {prj: set([role])})
    else:
        old_proj = eval(old_proj)
        if prj in old_proj:
            old_proj[prj].add(role)
        else:
            old_proj[prj] = set([role])
        st.execute('hset', mem, 'proj', old_proj)
    st.execute_pending()


#####################################


@st.collect('?r scm:repositoryId ?rid')
def add_repository((r, _, rid)):
    st.execute('hset', r, "id", rid.toPython())


@st.collect('?r doap:name ?name')
def add_repository_name((r, _, name)):
    prj = st.db.hget('tmp-rep', name.toPython())
    st.db.hdel('tmp-rep', name)
    st.execute('hset', r, "name", name)
    st.execute('sadd', prj + ':r:', r)


@st.collect('?r scm:firstCommit ?fc')
def add_repository_first_commit_info((r, _, fc)):
    timestamp = calendar.timegm(fc.toPython().timetuple())
    st.execute('hset', r, "first_commit", timestamp)


@st.collect('?r scm:lastCommit ?lc')
def add_repository_last_commit_info((r, _, lc)):
    timestamp = calendar.timegm(lc.toPython().timetuple())
    st.execute('hset', r, "last_commit", timestamp)
