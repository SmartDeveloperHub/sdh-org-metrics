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

from sdh.metrics.org import app, st as store
from sdh.metrics.server import ORG, SCM, CI, APIError
import calendar
from datetime import datetime

__author__ = 'Alejandro F. Carrera'


def get_average_list(l):
    return reduce(lambda x, y: x + y, l) / len(l)


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
        (int(a_begin) >= int(b_begin)) and (int(a_end) <= int(b_end))  # contains
    ) or (
        (int(a_begin) <= int(b_begin)) and (int(b_begin) <= int(a_end))  # shift right
    ) or (
        (int(a_begin) <= int(b_end)) and (int(b_end) <= int(a_end))  # shift left
    )


def detect_project_repositories_overlap(uri, args):
    temp_frame = store.get_project_temporal_frame(uri)
    return detect_overlap_date(
        args.get('begin'), args.get('end'),
        temp_frame.get('first_commit'), temp_frame.get('last_commit')
    )


def get_external_director_metric(uid, endpoint, aggregate, args, flag):
    try:
        pr = get_position_products(uid, args, 'directors', flag)
        pr_res = []
        if args['begin'] == 0:
            args['begin'] = None
        tmp_arg = args
        if flag:
            if aggregate == 'sum':
                tmp_frame = store.get_specific_products_temporal_frame(pr)
                tmp_arg['begin'] = tmp_frame.get('first_commit')
                tmp_arg['end'] = tmp_frame.get('last_commit')
                pr_res = map(
                    lambda x: app.request_metric(endpoint, prid=x.get('id'), **tmp_arg), pr
                )
            else:
                for k in pr:
                    pr_temp_frame = store.get_product_temporal_frame(k.get('uri'))
                    tmp_arg['begin'] = pr_temp_frame.get('first_commit')
                    tmp_arg['end'] = pr_temp_frame.get('last_commit')
                    pr_res.append(app.request_metric(endpoint, prid=k.get('id'), **tmp_arg))
        else:
            pr_res = map(lambda k: app.request_metric(endpoint, prid=k.get('id'), **tmp_arg), pr)
        if len(pr_res):
            context = pr_res[0][0]
        else:
            context = args
        v = zip(*map(lambda x: x[1], pr_res))
        if aggregate == 'avg':
            res = [get_average_list(x) for x in v]
        else:
            res = [sum(x) for x in v]
        return context, res
    except (EnvironmentError, AttributeError) as e:
        raise APIError(e.message)
    return args, []


def get_position_projects(uid, args, position, flag_total, only_uris):
    positions_id = store.get_all_members_id(position)
    if uid not in positions_id:
        return []
    else:
        projects = store.get_all_member_projects(positions_id[uid])
        if not flag_total:
            res_prj = set()
            for x in projects:
                if detect_project_repositories_overlap(x, args):
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


def get_director_roles(uid, args, role, flag_total):
    pr = set(get_position_projects(uid, args, 'directors', flag_total, True))
    members = store.get_all_members(role)
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


@app.view('/product-projects', target=ORG.Project, parameters=[ORG.Product],
          id='product-projects', title='Projects of Product')
def get_product_projects(prid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    products_id = store.get_all_products_id()
    if prid not in products_id:
        return args, []
    else:
        projects = store.get_all_product_projects(products_id[prid])
        if not flag_total:
            res_prj = set()
            for x in projects:
                if detect_project_repositories_overlap(x, args):
                    res_prj.add(x)
            projects = list(res_prj)
        res = []
        [res.append({
            'id': store.db.get(x),
            'uri': x
        }) for x in projects]
        return args, res


@app.view('/project-repositories', target=SCM.Repository, parameters=[ORG.Project],
          id='project-repositories', title='Repositories of Project')
def get_project_repositories(pjid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    products_id = store.get_all_projects_id()
    if pjid not in products_id:
        return args, []
    else:
        repos = store.get_all_project_repositories(products_id[pjid])
        if not flag_total:
            res_prj = set()
            for k in repos:
                rep_info = store.db.hgetall(k)
                if detect_overlap_date(
                    args.get('begin'), args.get('end'),
                    rep_info.get('first_commit'), rep_info.get('last_commit')
                ):
                    res_prj.add(k)
            repos = res_prj
        res = []
        [res.append({
            'id': store.db.hgetall(x).get('id'),
            'uri': x
        }) for x in repos]
        return args, res


@app.metric('/total-director-projects', parameters=[ORG.Person],
            id='director-projects', title='Projects of Director')
def get_total_director_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_position_projects(uid, args, 'directors', flag_total, False))]


@app.view('/director-projects', target=ORG.Project, parameters=[ORG.Person],
          id='director-projects', title='Projects of Director')
def get_director_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_projects(uid, args, 'directors', flag_total, False)


@app.metric('/total-architect-projects', parameters=[ORG.Person],
            id='architect-projects', title='Projects of Architect')
def get_total_architects_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_position_projects(uid, args, 'architects', flag_total, False))]


@app.view('/architect-projects', target=ORG.Project, parameters=[ORG.Person],
          id='architect-projects', title='Projects of Architect')
def get_architect_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_projects(uid, args, 'architects', flag_total, False)


@app.metric('/total-pmanager-projects', parameters=[ORG.Person],
            id='pmanager-projects', title='Projects of Product Manager')
def get_total_manager_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_position_projects(uid, args, 'productmanagers', flag_total, False))]


@app.view('/pmanager-projects', target=ORG.Project, parameters=[ORG.Person],
          id='pmanager-projects', title='Projects of Product Manager')
def get_manager_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_projects(uid, args, 'productmanagers', flag_total, False)


@app.metric('/total-director-products', parameters=[ORG.Person],
            id='director-products', title='Products of Director')
def get_total_director_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_position_products(uid, args, 'directors', flag_total))]


@app.view('/director-products', target=ORG.Product, parameters=[ORG.Person],
          id='director-products', title='Products of Director')
def get_director_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_products(uid, args, 'directors', flag_total)


@app.metric('/total-architect-products', parameters=[ORG.Person],
            id='architects-products', title='Products of Architect')
def get_total_architect_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_position_products(uid, args, 'architects', flag_total))]


@app.view('/architect-products', target=ORG.Product, parameters=[ORG.Person],
          id='architects-products', title='Products of Architect')
def get_architect_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_products(uid, args, 'architects', flag_total)


@app.metric('/total-pmanager-products', parameters=[ORG.Person],
            id='pmanager-products', title='Products of Product Manager')
def get_total_manager_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_position_products(uid, args, 'productmanagers', flag_total))]


@app.view('/pmanager-products', target=ORG.Product, parameters=[ORG.Person],
          id='pmanager-products', title='Products of Product Manager')
def get_manager_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_products(uid, args, 'productmanagers', flag_total)


@app.view('/director-productmanagers', target=ORG.Person, parameters=[ORG.Person],
          id='director-productmanagers', title='Product Managers of Director')
def get_director_pmanagers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_position(uid, args, 'productmanagers', flag_total)


@app.view('/director-architects', target=ORG.Person, parameters=[ORG.Person],
          id='director-architects', title='Architects of Director')
def get_director_architects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_position(uid, args, 'architects', flag_total)


@app.view('/director-developers', target=ORG.Person, parameters=[ORG.Person],
          id='director-developers', title='Developers of Director')
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


@app.metric('/director-activity', parameters=[ORG.Person],
            id='director-activity', title='Activity of Director')
def get_director_activity(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_director_metric(uid, 'sum-product-activity', 'sum', args, flag_total)


@app.metric('/director-quality', aggr='avg', parameters=[ORG.Person],
            id='director-quality', title='Quality of Director')
def get_director_quality(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_director_metric(uid, 'sum-product-quality', 'avg', args, flag_total)


@app.metric('/director-health', aggr='avg', parameters=[ORG.Person],
            id='director-health', title='Health of Director')
def get_director_health(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_director_metric(uid, 'sum-product-health', 'avg', args, flag_total)


@app.view('/pmanager-developers', target=ORG.Person, parameters=[ORG.Person],
          id='pmanager-developers', title='Developers of Product Manager')
def get_pmanager_developers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    try:
        res = set()
        pr = get_position_products(uid, args, 'productmanagers', flag_total)
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
