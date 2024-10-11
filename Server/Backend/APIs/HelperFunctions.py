import datetime 

def checkAPIInput(data, required_keys=[], accepted_keys=[]):
    dataKey = data.keys()
    for reqKey in required_keys:
        if not reqKey in dataKey:
            return False
    
    for key in dataKey:
        FoundKey = False
        if len(accepted_keys) == 0:
            continue
        
        for checkKey in accepted_keys:
            if checkKey == key:
                FoundKey = True
                break 
            elif checkKey.endswith("*") and key.startswith(checkKey[:-1]):
                FoundKey = True
                break 
            
        if not FoundKey:
            return False 

    return True 