import urllib.request
import json
import os

req = urllib.request.Request('https://api.github.com/repos/Aditya-9-6/GossipMesh/actions/runs')
req.add_header('Accept', 'application/vnd.github.v3+json')

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Total runs: {data.get('total_count')}")
        if data.get('workflow_runs'):
            run = data['workflow_runs'][0]
            print(f"Latest run ID: {run['id']}, status: {run['status']}, conclusion: {run['conclusion']}")
            print(f"Head branch: {run['head_branch']}")
            print(f"URL: {run['html_url']}")

            jobs_req = urllib.request.Request(run['jobs_url'])
            with urllib.request.urlopen(jobs_req) as jobs_response:
                jobs_data = json.loads(jobs_response.read().decode())
                for job in jobs_data['jobs']:
                    if job['conclusion'] != 'success':
                        print(f"Job failed: {job['name']}, status: {job['status']}, conclusion: {job['conclusion']}")
except Exception as e:
    print(f"Error fetching runs: {e}")
