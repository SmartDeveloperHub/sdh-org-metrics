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

from sdh.metrics.store.fragment import FragmentStore
from sdh.metrics.store.metrics import flat_sum
import calendar
from datetime import datetime
import uuid

__author__ = 'Alejandro F. Carrera'


class ORGStore(FragmentStore):
    def __init__(self, **kwargs):
        super(ORGStore, self).__init__(**kwargs)

    def get_all_members(self, position):
        res = set()
        r_keys = self.db.keys('*:m:' + position)
        for i in r_keys:
            res = res.union(set(self.db.smembers(i)))
        return list(res)

    def get_all_members_id(self, position):
        res = {}
        [res.update({self.db.hget(x, 'id'): x}) for x in self.get_all_members(position)]
        return res

    def get_all_member_projects(self, member_uri):
        proj = self.db.hget(member_uri, 'proj')
        if proj is None:
            return []
        else:
            return eval(proj)

    def get_all_products(self):
        res = set()
        r_keys = self.db.keys('*:p:')
        for i in r_keys:
            res = res.union(set(self.db.smembers(i)))
        return list(res)

    def get_all_products_id(self):
        res = {}
        [res.update({self.db.get(x): x}) for x in self.get_all_products()]
        return res

    def get_all_products_temporal_frame(self):
        pr = self.get_all_products()
        pr_fc = []
        pr_lc = []
        for x in pr:
            tf = self.get_product_temporal_frame(x)
            pr_fc.append(tf.get("first_commit"))
            pr_lc.append(tf.get("last_commit"))
        return {
            'first_commit': min(pr_fc), 'last_commit': max(pr_lc)
        }

    def get_specific_products_temporal_frame(self, products):
        pr_fc = []
        pr_lc = []
        for x in products:
            tf = self.get_product_temporal_frame(x.get('uri'))
            pr_fc.append(tf.get("first_commit"))
            pr_lc.append(tf.get("last_commit"))
        return {
            'first_commit': min(pr_fc), 'last_commit': max(pr_lc)
        }

    def get_all_product_projects(self, product_uri):
        return self.db.smembers(product_uri + ":pj:")

    def get_product_temporal_frame(self, product_uri):
        prj = self.get_all_product_projects(product_uri)
        prj_fc = []
        prj_lc = []
        for x in prj:
            prj_info = self.get_project_temporal_frame(x)
            prj_fc.append(prj_info.get("first_commit"))
            prj_lc.append(prj_info.get("last_commit"))
        return {
            'first_commit': min(prj_fc), 'last_commit': max(prj_lc)
        }

    def get_all_projects(self):
        res = set()
        r_keys = self.db.keys('*:pj:')
        for i in r_keys:
            res = res.union(set(self.db.smembers(i)))
        return list(res)

    def get_all_projects_id(self):
        res = {}
        [res.update({self.db.get(x): x}) for x in self.get_all_projects()]
        return res

    def get_all_project_products(self, project_uri):
        return self.db.smembers(project_uri + ":p:")

    def get_all_project_repositories(self, project_uri):
        return self.db.smembers(project_uri + ":r:")

    def get_project_temporal_frame(self, project_uri):
        rep = self.get_all_project_repositories(project_uri)
        rep_fc = []
        rep_lc = []
        for x in rep:
            rep_info = self.db.hgetall(x)
            rep_fc.append(rep_info.get("first_commit"))
            rep_lc.append(rep_info.get("last_commit"))
        if not len(rep_fc) and not len(rep_lc):
            return {
                'first_commit': 0, 'last_commit': 0
            }
        else:
            return {
                'first_commit': min(rep_fc), 'last_commit': max(rep_lc)
            }
