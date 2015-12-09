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
        'max': kwargs.get('max')
    }
    args['step'] = (args.get('end') - args.get('begin')) / args.get('max')
    return args


def detect_overlap_date(a_begin, a_end, b_begin, b_end):
    print ""
    return (
        (int(a_begin) <= int(b_begin)) and (int(a_end) >= int(b_end))  # contains
    ) or (
        (int(a_begin) <= int(b_begin)) and (int(b_begin) <= int(a_end))  # shift right
    ) or (
        (int(a_begin) <= int(b_end)) and (int(b_end) <= int(a_end))  # shift left
    )


def get_position_projects(uid, args, position, flag_total):
    positions_id = store.get_all_members_id(position)
    if uid not in positions_id:
        return args, []
    else:
        projects = store.get_all_member_projects(positions_id[uid])
        if flag_total:
            return projects
        else:
            res_prj = set()
            for x in projects:
                res_tmp = store.get_all_project_repositories(x)
                flag_do = True
                for k in res_tmp:
                    rep_info = store.db.hgetall(k)
                    if not detect_overlap_date(
                        args.get('begin'), args.get('end'),
                        rep_info.get('first_commit'), rep_info.get('last_commit')
                    ):
                        flag_do = False
                if flag_do:
                    res_prj.add(x)
            return list(res_prj)


def get_position_products(uid, args, position, flag_total):
    positions_id = store.get_all_members_id(position)
    if uid not in positions_id:
        return args, []
    else:
        pr = get_position_projects(uid, args, position, flag_total)
        res = set()
        for x in pr:
            res = res.union(set(store.get_all_project_products(x)))
        return res


@app.metric('/total-director-projects', parameters=[ORG.Person], id='director-projects', title='Projects')
def get_total_director_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_projects(uid, args, 'directors', flag_total))


@app.metric('/total-architects-projects', parameters=[ORG.Person], id='architects-projects', title='Projects')
def get_total_architects_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_projects(uid, args, 'architects', flag_total))


@app.metric('/total-pmanager-projects', parameters=[ORG.Person], id='pmanager-projects', title='Projects')
def get_total_manager_projects(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_projects(uid, args, 'productmanagers', flag_total))


@app.metric('/total-director-products', parameters=[ORG.Person], id='director-products', title='Products')
def get_total_director_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_products(uid, args, 'directors', flag_total))


@app.metric('/total-architects-products', parameters=[ORG.Person], id='architects-products', title='Products')
def get_total_architect_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_products(uid, args, 'architects', flag_total))


@app.metric('/total-pmanager-products', parameters=[ORG.Person], id='pmanager-products', title='Products')
def get_total_manager_products(uid, **kwargs):
    flag_total = kwargs.get('begin') is None and kwargs.get('end') is None
    args = get_correct_kwargs(kwargs)
    return args, len(get_position_products(uid, args, 'productmanagers', flag_total))
