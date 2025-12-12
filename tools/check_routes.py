from importlib import import_module

app = import_module('app.main').app

routes = [r.path for r in app.routes]
print('\n'.join(routes))
# print route names and endpoint
for r in app.routes:
    print(r.path, getattr(r.endpoint, '__name__', str(r.endpoint)))
