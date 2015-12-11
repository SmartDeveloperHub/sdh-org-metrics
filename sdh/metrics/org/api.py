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

__author__ = 'Fernando Serena'

from sdh.metrics.org import app, st as store
from sdh.metrics.store.metrics import aggregate, avg, flat_sum
from sdh.metrics.server import ORG, SCM, CI, APIError
import calendar
from datetime import datetime
import math


def get_correct_kwargs(kwargs):
    args = {
        'begin': 0 if kwargs.get('begin') is None else kwargs.get('begin'),
        'end': calendar.timegm(datetime.now().timetuple())
        if kwargs.get('end') is None else kwargs.get('end'),
        'max': 0 if kwargs.get('max') is None else kwargs.get('max')
    }
    if args['max'] == 0:
        args['step'] = 86400
    else:
        args['step'] = (args.get('end') - args.get('begin')) / args.get('max')
    return args


def detect_overlap_date(a_begin, a_end, b_begin, b_end):
    return (
        (int(a_begin) <= int(b_begin)) and (int(a_end) >= int(b_end))  # contains
    ) or (
        (int(a_begin) <= int(b_begin)) and (int(b_begin) <= int(a_end))  # shift right
    ) or (
        (int(a_begin) <= int(b_end)) and (int(b_end) <= int(a_end))  # shift left
    )


def get_position_projects(uid, args, position, flag_total, only_uris):
    positions_id = store.get_all_members_id(position)
    if uid not in positions_id:
        return []
    else:
        projects = store.get_all_member_projects(positions_id[uid])
        if not flag_total:
            res_prj = set()
            for x in projects:
                flag_do = False
                res_tmp = store.get_all_project_repositories(x)
                for k in res_tmp:
                    rep_info = store.db.hgetall(k)
                    if detect_overlap_date(
                        args.get('begin'), args.get('end'),
                        rep_info.get('first_commit'), rep_info.get('last_commit')
                    ):
                        flag_do = True
                        break
                if flag_do:
                    res_prj.add(x)
            projects = list(res_prj)
        res = []
        if only_uris:
            return projects
        else:
            [res.append({
                'id': store.db.get(x),
                'uri': x
            }) for x in projects]
            return res


def get_position_products(uid, args, position, flag_total):
    pr = get_position_projects(uid, args, position, flag_total, False)
    pro = set()
    res = []
    for x in pr:
        pro = pro.union(set(store.get_all_project_products(x.get('uri'))))
    [res.append({
        'id': store.db.get(x),
        'uri': x
    }) for x in pro]
    return res


def get_director_position(uid, args, position, flag_total):
    pr = set(get_position_projects(uid, args, 'directors', flag_total, True))
    members = store.get_all_members(position)
    members_dir = set()
    res = []
    for x in members:
        if len(pr.intersection(set(store.get_all_member_projects(x)))) > 0:
            members_dir.add(x)
    [res.append({
        'id': store.db.hgetall(x).get("id"),
        'uri': x
    }) for x in members_dir]
    return res


@app.metric('/total-director-projects', parameters=[ORG.Person],
            id='director-projects', title='Projects')
def get_total_director_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_projects(uid, args, 'directors', flag_total, False))


@app.view('/director-projects', target=ORG.Project, parameters=[ORG.Person],
          id='director-projects', title='Projects')
def get_director_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_projects(uid, args, 'directors', flag_total, False)


@app.metric('/total-architects-projects', parameters=[ORG.Person],
            id='architects-projects', title='Projects')
def get_total_architects_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_projects(uid, args, 'architects', flag_total, False))


@app.view('/architects-projects', target=ORG.Project, parameters=[ORG.Person],
          id='architects-projects', title='Projects')
def get_architect_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_projects(uid, args, 'architects', flag_total, False)


@app.metric('/total-pmanager-projects', parameters=[ORG.Person],
            id='pmanager-projects', title='Projects')
def get_total_manager_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_projects(uid, args, 'productmanagers', flag_total, False))


@app.view('/pmanager-projects', target=ORG.Project, parameters=[ORG.Person],
          id='pmanager-projects', title='Projects')
def get_manager_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_projects(uid, args, 'productmanagers', flag_total, False)


# TODO: Metrica de projects en los que colabora un developer
@app.metric('/developer-projects', parameters=[ORG.Person],
            id='developer-projects', title='Projects')
def get_total_developer_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, 0


# TODO: Vista de projects en los que colabora un developer
@app.view('/developer-projects', target=ORG.Product, parameters=[ORG.Person],
          id='developer-projects', title='Projects')
def get_developer_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, []


@app.metric('/total-director-products', parameters=[ORG.Person],
            id='director-products', title='Products')
def get_total_director_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_products(uid, args, 'directors', flag_total))


@app.view('/director-products', target=ORG.Product, parameters=[ORG.Person],
          id='director-products', title='Products')
def get_director_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_products(uid, args, 'directors', flag_total)


@app.metric('/total-architects-products', parameters=[ORG.Person],
            id='architects-products', title='Products')
def get_total_architect_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_products(uid, args, 'architects', flag_total))


@app.view('/architects-products', target=ORG.Product, parameters=[ORG.Person],
          id='architects-products', title='Products')
def get_architect_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_products(uid, args, 'architects', flag_total)


@app.metric('/total-pmanager-products', parameters=[ORG.Person],
            id='pmanager-products', title='Products')
def get_total_manager_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_products(uid, args, 'productmanagers', flag_total))


@app.view('/pmanager-products', target=ORG.Product, parameters=[ORG.Person],
          id='pmanager-products', title='Products')
def get_manager_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_products(uid, args, 'productmanagers', flag_total)


@app.view('/director-productmanagers', target=ORG.Person, parameters=[ORG.Person],
          id='director-productmanagers', title='Director Managers')
def get_director_pmanagers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_position(uid, args, 'productmanagers', flag_total)


@app.view('/director-architects', target=ORG.Person, parameters=[ORG.Person],
          id='director-architects', title='Director Architects')
def get_director_architects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_position(uid, args, 'architects', flag_total)


@app.view('/director-developers', target=ORG.Person, parameters=[ORG.Person],
          id='director-developers', title='Director Developers')
def get_director_developers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    try:
        res = set()
        pr = get_position_products(uid, args, 'directors', flag_total)
        devs = map(lambda k: app.request_view('product-developers', prid=k.get('id'), **kwargs), pr)
        [[res.add(j.get('uri')) for j in x] for x in map(lambda x: x[1], devs)]
        res_devs = []
        [res_devs.append({
            "id": store.db.hgetall(x).get("id"),
            "uri": x
        }) for x in res]
        return args, res_devs
    except (EnvironmentError, AttributeError) as e:
        raise APIError(e.message)
    return args, []
