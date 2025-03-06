shared_state = {
}

def setParam(param, value):
    shared_state[param] = value

def getParam(param):
    if param in shared_state:
        return shared_state[param]
    else:
        return None