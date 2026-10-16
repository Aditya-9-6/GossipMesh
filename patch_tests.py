import sys

with open('tests/api/routers/test_repositories.py', 'r') as f:
    content = f.read()

content = content.replace('''
            response.json()['error']['message'],
            'Not authorized for this organization'
''', '''
            response.json(),
            {
                "error": {
                    "code": "AUTHORIZATION_ERROR",
                    "message": "Not authorized for this organization"
                }
            }
''')

with open('tests/api/routers/test_repositories.py', 'w') as f:
    f.write(content)