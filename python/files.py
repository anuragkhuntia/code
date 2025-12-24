import json

def json_open(path):
    with open(path,"r") as f:
        return json.load(f)

def json_write(path,data):
    with open(path,"w") as f:
        return json.dump(data, f)

def json_keys(data):
    for key in data.keys():
        print(key)


def main():
    data = json_open("data.json")
    print(f"data : \n {data}")

    json_keys(data)

    for k,v in data.items():
        print(f"{k}:{v}")
    
    for k in data.values():
        print(k)

    data["server3"] = {
        "hostname" : "compute03",
        "ram" : 128,
        "vcpu" : 256,
        "disk" : 500
    }
    
    json_write("data.json",data)


if __name__ == "__main__":
    main()