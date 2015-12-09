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

    def get_all_project_repositories(self, project_uri):
        return self.db.smembers(project_uri + ":r:")

    def get_all_project_products(self, project_uri):
        return self.db.smembers(project_uri + ":p:")
