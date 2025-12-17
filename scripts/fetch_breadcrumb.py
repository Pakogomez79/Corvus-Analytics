import requests
r = requests.get('http://127.0.0.1:8000/entidades')
print('status', r.status_code)
html = r.text
start = html.find('<nav class="header-breadcrumb">')
if start!=-1:
    end = html.find('</nav>', start)
    print(html[start:end+6])
else:
    print('breadcrumb not found')
