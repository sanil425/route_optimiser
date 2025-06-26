import requests

url = "http://127.0.0.1:5000/solve"

data = {
    "instruction": (
        "I want to leave from Home (19 Hannum Drive, Ardmore, PA) as late as possible to pick up my friend from Ardmore Station (39 Station Rd, Ardmore, PA), exactly at 1736 hrs, and stop for 3 minutes, "
        "Go grocery shopping at Trader Joe's (112 Coulter Ave, Ardmore, PA) for 25 minutes. It's open from 0800 hrs to 2100 hrs, "
        "Stop at CVS (119 E Lancaster Ave, Ardmore, PA) for 10 minutes. It's open from 0900 hrs to 2100 hrs, "
        "Return home."
    )
}

# Send the POST request
response = requests.post(url, json=data)

# Display result
if response.status_code == 200:
    print("✅ Success! Response:")
    print(response.json())
else:
    print(f"❌ Request failed with status {response.status_code}")
    print(response.text)
