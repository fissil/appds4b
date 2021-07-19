___author___ = "Nikolay Zaytsev nzaytsev@cisco.com"

import requests
import os
import json
import time
import configparser
import subprocess

config = configparser.ConfigParser()
config.read('config.ini')

class GeneralAppdConnector(object):

    def __init__(self):
        self.host = config['DEFAULT']['host']
        self.port = config['DEFAULT']['port']
        self.path = config['DEFAULT']['path']
        self.headers = { "Content-Type": "application/json" }

    def postData(self, data):
        print("Posting: {}".format(data))
        r = requests.post("http://{}:{}{}".format(self.host,
                                                  self.port,
                                                  self.path),
                          data=json.dumps(data), headers=self.headers)
        print("Post result {}".format(r))

class S4B(object):
    def __init__(self):
        self.out = None
        self.err = None
        self.script = config['skype_pwsh']['script']
        self.parameters = config['skype_pwsh']['parameters'].split()
        self.pools_list = None
        self.agent_dict = dict()
        self.pool_servers_dict = dict()
        self.total_connections = None
        self.users_connected = None
        self.client_versions_connected = None
        self.connector = GeneralAppdConnector()

    def getData(self):
        command = ["powershell.exe", self.script] + [param for param in self.parameters]
        p = subprocess.Popen(command, stdout=subprocess.PIPE)
        self.out, self.err = p.communicate()
        out_lists = self.out.split('\n')
        print("Getting result {}".format(out_lists))
        for index, line in enumerate(out_lists):
            if 'Checking these pool servers' in line:
                end_index = index + out_lists[index:].index('\r')
                self.pools_list = out_lists[index+1:end_index]
            elif 'Agent' in line:
                end_index = index + 1 + out_lists[index + 2:].index('\r')
                agent_list = out_lists[index + 2:end_index]
                for agent in agent_list:
                    agl = agent.split()
                    self.agent_dict[agl[-2]] = agl[-1]
            elif 'Front End Servers' in line:
                end_index = index + out_lists[index + 2:].index('\r')
                pool_servers_list = out_lists[index + 2:end_index]
                for server in pool_servers_list:
                    srv = server.split()
                    self.pool_servers_dict[srv[0]] = srv[-2]
                self.total_connections = out_lists[end_index+1].split()[2]
                self.users_connected = out_lists[end_index+6].split()[2]
                self.client_versions_connected = out_lists[end_index+7].split()[3]

    def getDataTest(self):
        f = open('result.txt', 'rb')
        out_str = f.read().decode('utf-8', 'replace')
        out_lists = out_str.split('\n')
        for index, line in enumerate(out_lists):
            if 'Checking these pool servers' in line:
                end_index = index + out_lists[index:].index('\r')
                self.pools_list = out_lists[index + 1:end_index]
            elif 'Agent' in line:
                end_index = index + 1 + out_lists[index + 2:].index('\r')
                agent_list = out_lists[index + 2:end_index]
                for agent in agent_list:
                    agl = agent.split()
                    self.agent_dict[agl[-2]] = agl[-1]
            elif 'Front End Servers' in line:
                end_index = index + out_lists[index + 2:].index('\r')
                pool_servers_list = out_lists[index + 2:end_index]
                for server in pool_servers_list:
                    srv = server.split()
                    self.pool_servers_dict[srv[0]] = srv[-2]
                self.total_connections = out_lists[end_index + 1].split()[2]
                self.users_connected = out_lists[end_index + 6].split()[2]
                self.client_versions_connected = out_lists[end_index + 7].split()[3]

    @staticmethod
    def cookMetricData(pools_list, agent_dict, server_dict, total_connections, users_connected,
                       client_versions_connected):
        metric_data = []
        for index, pool in enumerate(pools_list):
            metric = {"metricName": "Custom Metrics|SKYPEPOOLS|{}".format(pool),
                      "aggregatorType": "OBSERVATION",
                      "value": index
                      }
            metric_data.append(metric)
        for agent_name, number in agent_dict.items():
            metric = {"metricName": "Custom Metrics|SKYPEAGENTS|{}".format(agent_name),
                      "aggregatorType": "OBSERVATION",
                      "value": int(number)
                      }
            metric_data.append(metric)
        for server_name, number in server_dict.items():
            metric = {"metricName": "Custom Metrics|SKYPESERVERS|{}".format(server_name),
                      "aggregatorType": "OBSERVATION",
                      "value": int(number)
                      }
            metric_data.append(metric)
        metric_tc = {"metricName": "Custom Metrics|SKYPETC|TOTAL_CONNETIONS",
                     "aggregatorType": "OBSERVATION",
                     "value": int(total_connections)
                     }
        metric_uc = {"metricName": "Custom Metrics|SKYPETC|USERS_CONNECTED",
                     "aggregatorType": "OBSERVATION",
                     "value": int(users_connected)
                     }
        metric_cvc = {"metricName": "Custom Metrics|SKYPETC|CLIENT_VERSIONS_CONNECTED",
                      "aggregatorType": "OBSERVATION",
                      "value": int(client_versions_connected)
                      }
        metric_data = metric_data + [metric_tc, metric_uc, metric_cvc]
        return metric_data

    def sendData(self):
        metric_data = self.cookMetricData(self.pools_list, self.agent_dict, self.pool_servers_dict,
                                          self.total_connections, self.users_connected, self.client_versions_connected)
        self.connector.postData(metric_data)

if __name__ == "__main__":
    s4b = S4B()
    s4b.getData()
    s4b.sendData()
