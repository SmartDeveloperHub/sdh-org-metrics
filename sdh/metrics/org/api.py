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


def get_external_position_metric(uid, endpoint, position, aggregate, args, flag):
    try:
        pr = get_position_products(uid, args, position, flag)
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


def get_position_repositories(uid, args, position, flag_total, only_uris):
    positions_id = store.get_all_members_id(position)
    if uid not in positions_id:
        return []
    else:
        projects = store.get_all_member_projects(positions_id[uid])
        res_prj = set()
        res = []
        for x in projects:
            repos = store.get_all_project_repositories(x)
            if not flag_total:

                for k in repos:
                    rep_info = store.db.hgetall(k)
                    if detect_overlap_date(
                        args.get('begin'), args.get('end'),
                        rep_info.get('first_commit'), rep_info.get('last_commit')
                    ):
                        res_prj.add(k)
        if only_uris:
            return res_prj
        else:
            [res.append({
                'id': store.db.hgetall(x).get('id'),
                'uri': x
            }) for x in res_prj]
            return res


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


def get_position_position(uid, args, fil, position, flag_total):
    pr = set(get_position_projects(uid, args, fil, flag_total, True))
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


def get_director_position(uid, args, position, flag_total):
    return get_position_position(uid, args, 'directors', position, flag_total)


def get_pmanager_position(uid, args, position, flag_total):
    return get_position_position(uid, args, 'productmanagers', position, flag_total)


def get_director_roles(uid, args, role, flag_total):
    return get_position_position(uid, args, 'directors', role, flag_total)


def get_pmanager_roles(uid, args, role, flag_total):
    return get_position_position(uid, args, 'productmanagers', role, flag_total)


def helper_get_director_pmanagers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_position(uid, args, 'productmanagers', flag_total)


def helper_get_director_architects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_position(uid, args, 'architects', flag_total)


def helper_get_pmanager_architects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_pmanager_position(uid, args, 'architects', flag_total)


def helper_get_position_developers(uid, position, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    try:
        res = set()
        pr = get_position_products(uid, args, position, flag_total)
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
    projects_id = store.get_all_projects_id()
    if pjid not in projects_id:
        return args, []
    else:
        repos = store.get_all_project_repositories(projects_id[pjid])
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


@app.metric('/total-director-repositories', parameters=[ORG.Person],
            id='director-repositories', title='Repositories of Director')
def get_total_director_repositories(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_position_repositories(uid, args, 'directors', flag_total, False))]


@app.view('/director-repositories', target=SCM.Repository, parameters=[ORG.Person],
          id='director-repositories', title='Repositories of Director')
def get_director_repositories(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_repositories(uid, args, 'directors', flag_total, False)


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


@app.metric('/total-pmanager-repositories', parameters=[ORG.Person],
            id='pmanager-repositories', title='Repositories of Product Manager')
def get_total_pmanager_repositories(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_position_repositories(uid, args, 'productmanagers', flag_total, False))]


@app.view('/pmanager-repositories', target=SCM.Repository, parameters=[ORG.Person],
          id='pmanager-repositories', title='Repositories of Product Manager')
def get_pmanager_repositories(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_position_repositories(uid, args, 'productmanagers', flag_total, False)


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


@app.metric('/total-director-productmanagers', parameters=[ORG.Person],
            id='director-productmanagers', title='Product Managers of Director')
def get_total_director_pmanagers(uid, **kwargs):
    co, res = helper_get_director_pmanagers(uid, **kwargs)
    return co, [len(res)]


@app.view('/director-productmanagers', target=ORG.Person, parameters=[ORG.Person],
          id='director-productmanagers', title='Product Managers of Director')
def get_director_pmanagers(uid, **kwargs):
    return helper_get_director_pmanagers(uid, **kwargs)


@app.metric('/total-director-architects', parameters=[ORG.Person],
            id='director-architects', title='Architects of Director')
def get_total_director_architects(uid, **kwargs):
    co, res = helper_get_director_architects(uid, **kwargs)
    return co, [len(res)]


@app.view('/director-architects', target=ORG.Person, parameters=[ORG.Person],
          id='director-architects', title='Architects of Director')
def get_director_architects(uid, **kwargs):
    return helper_get_director_architects(uid, **kwargs)


@app.metric('/total-director-developers', parameters=[ORG.Person],
            id='director-developers', title='Developers of Director')
def get_total_director_developers(uid, **kwargs):
    co, res = helper_get_position_developers(uid, 'directors', **kwargs)
    return co, [len(res)]


@app.view('/director-developers', target=ORG.Person, parameters=[ORG.Person],
          id='director-developers', title='Developers of Director')
def get_director_developers(uid, **kwargs):
    return helper_get_position_developers(uid, 'directors', **kwargs)


@app.metric('/total-director-stakeholders', parameters=[ORG.Person],
            id='director-stakeholders', title='Stakeholders of Director')
def get_total_director_stakeholders(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_director_roles(uid, args, 'stakeholder', flag_total))]


@app.view('/director-stakeholders', target=ORG.Person, parameters=[ORG.Person],
          id='director-stakeholders', title='Stakeholders of Director')
def get_director_stakeholders(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_roles(uid, args, 'stakeholder', flag_total)


@app.metric('/total-director-swarchitects', parameters=[ORG.Person],
            id='director-swarchitects', title='Software Architects of Director')
def get_total_director_swarchitects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_director_roles(uid, args, 'softwarearchitect', flag_total))]


@app.view('/director-swarchitects', target=ORG.Person, parameters=[ORG.Person],
          id='director-swarchitects', title='Software Architects of Director')
def get_director_swarchitects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_roles(uid, args, 'softwarearchitect', flag_total)


@app.metric('/total-director-swdevelopers', parameters=[ORG.Person],
            id='director-swdevelopers', title='Software Developers of Director')
def get_total_director_swdevelopers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_director_roles(uid, args, 'softwaredeveloper', flag_total))]


@app.view('/director-swdevelopers', target=ORG.Person, parameters=[ORG.Person],
          id='director-swdevelopers', title='Software Developers of Director')
def get_director_swdevelopers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_roles(uid, args, 'softwaredeveloper', flag_total)


@app.metric('/total-director-pjmanagers', parameters=[ORG.Person],
            id='director-pjmanagers', title='Project Managers of Director')
def get_total_director_pjmanagers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_director_roles(uid, args, 'projectmanager', flag_total))]


@app.view('/director-pjmanagers', target=ORG.Person, parameters=[ORG.Person],
          id='director-pjmanagers', title='Project Managers of Director')
def get_director_pjmanagers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_director_roles(uid, args, 'projectmanager', flag_total)


@app.metric('/total-director-members', parameters=[ORG.Person],
            id='director-members', title='Members below Director')
def get_total_director_members(uid, **kwargs):
    res = {}
    co, pm = helper_get_director_pmanagers(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in pm]
    co, ar = helper_get_director_architects(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in ar]
    co, dev = helper_get_position_developers(uid, 'directors', **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in dev]
    return co, [len(res.keys())]


@app.view('/director-members', target=ORG.Person, parameters=[ORG.Person],
          id='director-members', title='Members below Director')
def get_director_members(uid, **kwargs):
    res = {}
    co, pm = helper_get_director_pmanagers(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in pm]
    co, ar = helper_get_director_architects(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in ar]
    co, dev = helper_get_position_developers(uid, 'directors', **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in dev]
    res_mem = []
    [res_mem.append({
        "id": x,
        "uri": res[x]
    }) for x in res.keys()]
    return co, res_mem


@app.metric('/director-productmembers', aggr='avg', parameters=[ORG.Person],
            id='director-productmembers', title='Product Members AVG of Director')
def get_avg_director_productmembers(uid, **kwargs):

    res = {}
    co, pm = helper_get_director_pmanagers(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in pm]
    co, ar = helper_get_director_architects(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in ar]
    co, dev = helper_get_position_developers(uid, 'directors', **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in dev]
    res_mem = len(res.keys())

    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    res_pr = len(get_position_products(uid, args, 'directors', flag_total))

    if res_pr == 0:
        return co, [0]

    return co, [float(res_mem) / float(res_pr)]


@app.metric('/director-productrepositories', aggr='avg', parameters=[ORG.Person],
            id='director-productrepositories', title='Product Repositories AVG of Director')
def get_avg_director_productrepositories(uid, **kwargs):

    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    res_rep = len(get_position_repositories(uid, args, 'directors', flag_total, True))

    res_pr = len(get_position_products(uid, args, 'directors', flag_total))

    if res_pr == 0:
        return args, [0]

    return args, [float(res_rep) / float(res_pr)]


@app.metric('/director-projectmembers', aggr='avg', parameters=[ORG.Person],
            id='director-projectmembers', title='Project Members AVG of Director')
def get_avg_director_projectmembers(uid, **kwargs):

    res = {}
    co, pm = helper_get_director_pmanagers(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in pm]
    co, ar = helper_get_director_architects(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in ar]
    co, dev = helper_get_position_developers(uid, 'directors', **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in dev]
    res_mem = len(res.keys())

    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    res_pr = len(get_position_projects(uid, args, 'directors', flag_total, True))

    if res_pr == 0:
        return co, [0]

    return co, [float(res_mem) / float(res_pr)]


@app.metric('/director-projectrepositories', aggr='avg', parameters=[ORG.Person],
            id='director-projectrepositories', title='Project Repositories AVG of Director')
def get_avg_director_projectrepositories(uid, **kwargs):

    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    res_rep = len(get_position_repositories(uid, args, 'directors', flag_total, True))

    res_pr = len(get_position_projects(uid, args, 'directors', flag_total, True))

    if res_pr == 0:
        return args, [0]

    return args, [float(res_rep) / float(res_pr)]


@app.metric('/director-activity', parameters=[ORG.Person],
            id='director-activity', title='Activity of Director')
def get_director_activity(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-activity', 'directors', 'sum', args, flag_total)


@app.metric('/director-quality', aggr='avg', parameters=[ORG.Person],
            id='director-quality', title='Quality of Director')
def get_director_quality(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-quality', 'directors', 'avg', args, flag_total)


@app.metric('/director-health', aggr='avg', parameters=[ORG.Person],
            id='director-health', title='Health of Director')
def get_director_health(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-health', 'directors', 'avg', args, flag_total)


@app.metric('/director-costs', parameters=[ORG.Person],
            id='director-costs', title='Costs of Director')
def get_director_costs(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-cost', 'directors', 'sum', args, flag_total)


@app.metric('/director-externals', parameters=[ORG.Person],
            id='director-externals', title='External Committers from Products of Director')
def get_director_externals(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-externals', 'directors', 'sum', args, flag_total)


@app.metric('/director-timetomarket', aggr='avg', parameters=[ORG.Person],
            id='director-timetomarket', title='Time To Market from Products of Director')
def get_director_timetomarket(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-timetomarket', 'directors', 'avg', args, flag_total)


@app.metric('/total-pmanager-architects', parameters=[ORG.Person],
            id='pmanager-architects', title='Architects of Product Manager')
def get_total_pmanager_architects(uid, **kwargs):
    co, res = helper_get_pmanager_architects(uid, **kwargs)
    return co, [len(res)]


@app.view('/pmanager-architects', target=ORG.Person, parameters=[ORG.Person],
          id='pmanager-architects', title='Architects of Product Manager')
def get_pmanager_architects(uid, **kwargs):
    return helper_get_pmanager_architects(uid, **kwargs)


@app.metric('/total-pmanager-developers', parameters=[ORG.Person],
            id='pmanager-developers', title='Developers of Product Manager')
def get_total_pmanager_developers(uid, **kwargs):
    co, res = helper_get_position_developers(uid, 'productmanagers', **kwargs)
    return co, [len(res)]


@app.view('/pmanager-developers', target=ORG.Person, parameters=[ORG.Person],
          id='pmanager-developers', title='Developers of Product Manager')
def get_pmanager_developers(uid, **kwargs):
    return helper_get_position_developers(uid, 'productmanagers', **kwargs)


@app.metric('/total-pmanager-stakeholders', parameters=[ORG.Person],
            id='pmanager-stakeholders', title='Stakeholders of Product Manager')
def get_total_pmanager_stakeholders(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_pmanager_roles(uid, args, 'stakeholder', flag_total))]


@app.view('/pmanager-stakeholders', target=ORG.Person, parameters=[ORG.Person],
          id='pmanager-stakeholders', title='Stakeholders of Product Manager')
def get_pmanager_stakeholders(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_pmanager_roles(uid, args, 'stakeholder', flag_total)


@app.metric('/total-pmanager-swarchitects', parameters=[ORG.Person],
            id='pmanager-swarchitects', title='Software Architects of Product Manager')
def get_total_pmanager_swarchitects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_pmanager_roles(uid, args, 'softwarearchitect', flag_total))]


@app.view('/pmanager-swarchitects', target=ORG.Person, parameters=[ORG.Person],
          id='pmanager-swarchitects', title='Software Architects of Product Manager')
def get_pmanager_swarchitects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_pmanager_roles(uid, args, 'softwarearchitect', flag_total)


@app.metric('/total-pmanager-swdevelopers', parameters=[ORG.Person],
            id='pmanager-swdevelopers', title='Software Developers of Product Manager')
def get_total_pmanager_swdevelopers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_pmanager_roles(uid, args, 'softwaredeveloper', flag_total))]


@app.view('/pmanager-swdevelopers', target=ORG.Person, parameters=[ORG.Person],
          id='pmanager-swdevelopers', title='Software Developers of Product Manager')
def get_pmanager_swdevelopers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_pmanager_roles(uid, args, 'softwaredeveloper', flag_total)


@app.metric('/total-pmanager-pjmanagers', parameters=[ORG.Person],
          id='pmanager-pjmanagers', title='Project Managers of Product Manager')
def get_total_pmanager_pjmanagers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, [len(get_pmanager_roles(uid, args, 'projectmanager', flag_total))]


@app.view('/pmanager-pjmanagers', target=ORG.Person, parameters=[ORG.Person],
          id='pmanager-pjmanagers', title='Project Managers of Product Manager')
def get_pmanager_pjmanagers(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, get_pmanager_roles(uid, args, 'projectmanager', flag_total)


@app.metric('/total-pmanager-members', parameters=[ORG.Person],
            id='pmanager-members', title='Members below Product Manager')
def get_total_pmanager_members(uid, **kwargs):
    res = {}
    co, ar = helper_get_pmanager_architects(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in ar]
    co, dev = helper_get_position_developers(uid, 'productmanagers', **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in dev]
    return co, [len(res.keys())]


@app.metric('/pmanager-productrepositories', aggr='avg', parameters=[ORG.Person],
            id='pmanager-productrepositories', title='Product Repositories AVG of Product Manager')
def get_avg_pmanager_productrepositories(uid, **kwargs):

    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    res_rep = len(get_position_repositories(uid, args, 'productmanagers', flag_total, True))

    res_pr = len(get_position_products(uid, args, 'productmanagers', flag_total))

    if res_pr == 0:
        return args, [0]

    return args, [float(res_rep) / float(res_pr)]


@app.metric('/pmanager-productmembers', aggr='avg', parameters=[ORG.Person],
            id='pmanager-productmembers', title='Product Members AVG of Product Manager')
def get_avg_pmanager_productmembers(uid, **kwargs):

    res = {}
    co, ar = helper_get_pmanager_architects(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in ar]
    co, dev = helper_get_position_developers(uid, 'productmanagers', **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in dev]
    res_mem = len(res.keys())

    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    res_pr = len(get_position_products(uid, args, 'productmanagers', flag_total))

    if res_pr == 0:
        return co, [0]

    return co, [float(res_mem) / float(res_pr)]


@app.metric('/pmanager-projectrepositories', aggr='avg', parameters=[ORG.Person],
            id='pmanager-projectrepositories', title='Project Repositories AVG of Product Manager')
def get_avg_pmanager_projectrepositories(uid, **kwargs):

    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    res_rep = len(get_position_repositories(uid, args, 'productmanagers', flag_total, True))

    res_pr = len(get_position_projects(uid, args, 'productmanagers', flag_total, True))

    if res_pr == 0:
        return args, [0]

    return args, [float(res_rep) / float(res_pr)]


@app.metric('/pmanager-projectmembers', aggr='avg', parameters=[ORG.Person],
            id='pmanager-projectmembers', title='Project Members AVG of Product Manager')
def get_avg_pmanager_projectmembers(uid, **kwargs):

    res = {}
    co, ar = helper_get_pmanager_architects(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in ar]
    co, dev = helper_get_position_developers(uid, 'productmanagers', **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in dev]
    res_mem = len(res.keys())

    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    res_pr = len(get_position_projects(uid, args, 'productmanagers', flag_total, True))

    if res_pr == 0:
        return co, [0]

    return co, [float(res_mem) / float(res_pr)]


@app.view('/pmanager-members', target=ORG.Person, parameters=[ORG.Person],
          id='pmanager-members', title='Members below Product Manager')
def get_pmanager_members(uid, **kwargs):
    res = {}
    co, ar = helper_get_pmanager_architects(uid, **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in ar]
    co, dev = helper_get_position_developers(uid, 'productmanagers', **kwargs)
    [res.update({x.get('id'): x.get('uri')}) for x in dev]
    res_mem = []
    [res_mem.append({
        "id": x,
        "uri": res[x]
    }) for x in res.keys()]
    return co, res_mem


@app.metric('/pmanager-activity', parameters=[ORG.Person],
            id='pmanager-activity', title='Activity of Product Manager')
def get_pmanager_activity(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-activity', 'productmanagers', 'sum', args, flag_total)


@app.metric('/pmanager-quality', aggr='avg', parameters=[ORG.Person],
            id='pmanager-quality', title='Quality of Product Manager')
def get_pmanager_quality(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-quality', 'productmanagers', 'avg', args, flag_total)


@app.metric('/pmanager-health', aggr='avg', parameters=[ORG.Person],
            id='pmanager-health', title='Health of Product Manager')
def get_pmanager_health(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-health', 'productmanagers', 'avg', args, flag_total)


@app.metric('/pmanager-costs', parameters=[ORG.Person],
            id='pmanager-costs', title='Costs of Product Manager')
def get_pmanager_costs(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-cost', 'productmanagers', 'sum', args, flag_total)


@app.metric('/pmanager-timetomarket', aggr='avg', parameters=[ORG.Person],
            id='pmanager-timetomarket', title='Time To Market from Products of Product Manager')
def get_pmanager_timetomarket(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return get_external_position_metric(uid, 'sum-product-timetomarket', 'productmanagers', 'avg', args, flag_total)
