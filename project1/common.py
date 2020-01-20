import json

def readjson():
    with open('config.json') as json_file:
        data = json.load(json_file)

    data['server']['port'] = int(data['server']['port'])
    for client in data['clients']:
    	client['port'] = int(client['port'])
    return data