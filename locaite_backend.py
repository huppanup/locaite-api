import shutil
from flask import Flask, request, jsonify
import requests, threading, logging
from typing import Dict, Any

import os

from global_constant import *

app = Flask(__name__)

logger = logging.getLogger('locaite_logger')
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler('locaite_output.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Disable propagation to the root logger
logger.propagate = False

def is_missing_keys(list, required_keys):
    return [key for key in required_keys if key not in list]

@app.route('/')
def index():
    return "Server is running"

@app.route('/training/start', methods=['POST'])
def start_training():
    data = request.get_json()

    if (k := is_missing_keys(data, ["id"])):
        return {'code' : 400, 'message': f"Missing required data: {', '.join(k)}"}, 400
    
    # Fetch training data info
    if len(data) == 1 :
        try: 
            data = requests.get(
                BASE_URL + GET_TRAINING_SOURCE,
                params= {'id':data["id"]},
                headers= { 'x-app-key': APP_KEY, 'Content-Type': 'application/json' })
            data = data.json()
            if data["code"] != 200:
                return data, data["code"]
            else:
                data = data["data"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Error while fetching training data info. {str(e)}")
            return {"code" : 500, "message" : str(e)}, 500
    
    # Download training data
    if (k := is_missing_keys(data, ["id", "files", "fromDate", "toDate", "dataUrl"])):
        return {'code' : 400, 'message': f"Missing required data: {', '.join(k)}"}, 400
    try: 
        response = requests.get(data["dataUrl"])
        if response.status_code == 200:
            os.makedirs(TRAINING_DATA_PATH, exist_ok=True)
            with open(f'{TRAINING_DATA_PATH}/{data["id"]}.zip', 'wb') as file:
                file.write(response.content)
        else:
            return {"code":400,'message': "Invalid download link provided."}, 400
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while fetching source data info. {str(e)}")
        return {"code" : 500, "message" : str(e)}, 500

    try:
        shutil.unpack_archive(f'{TRAINING_DATA_PATH}/{data["id"]}.zip', f'{TRAINING_DATA_PATH}/{data["id"]}', 'zip')
        if ( k := is_missing_keys(os.listdir(f'{TRAINING_DATA_PATH}/{data["id"]}'), data["files"])):
            return {'code' : 400, 'message': f"Missing files: {', '.join(k)}"}, 400
        # TODO: Replace with actual model training
        # threading.Thread(target=train_model, args=(f'./{data["id"]}.zip')).start()
        logger.info(f"Created data: {data["id"]}")
        return {"code":201,'message': "Training data created."}, 201
    finally: 
        os.remove(f'{TRAINING_DATA_PATH}/{data["id"]}.zip')

def submit_augmentation(task_id, ap_path, gt_path):
    # ap_path: ap_name_list file path.pt filepath of 1-d array of bssid
    # gt_path: output_list file path. N-ndNumpyArray, [bssid_index][x][y] = rssi of bssid on x,y (meter_x, meter_y fr>
    try:
        result = subprocess.Popen(f"python3 /home/anton/aug_pipeline/submit.py --augment -t {task_id} -a {ap_path} -g {gt_path}")
        if result.returncode != 0:
            logger.error("[Return code %d] Failed to submit result", result.returncode)
    except Exception as e:
        logger.exception("Error executing script: %s", e)
    return

def submit_crowdsource(task_id, floor_data):
    # floor_data : list of result, format : [file_path], [floor_index], [utm50q_e], [utm50q_n]
    floor_args = ' '.join([f" -f {file_path}, {floor_index}, {utm50q_e}, {utm50q_n}" for file_path, floor_index, utm50q_e, utm50q_e, utm50q_n in floor_data])
    subprocess.Popen(f"python3 /home/anton/aug_pipeline/submit.py --crowdsource -t {task_id}{floor_args}", shell=True)
    return

# CODE FOR OLD PIPELINE, DO NOT USE
'''
# TODO: Use this to dispatch checkpoint status
def dispatch_status(id: str, status: STATUS, message: str):
    headers = { 'x-app-key': APP_KEY, 'Content-Type': 'application/json' }
    data = { "id": id, "status": status, "message": message }

    try:
        response = requests.put(BASE_URL+PUT_TRAINING_STATUS, headers=headers, json=data)

        if response.status_code != 200:
            response = response.json()
            print(f"Could not update status to server.\n\tError code : {response['code']}\n\tMessage: {response['message']}")

    except requests.exceptions.RequestException as e:
        print(f"Error while updating status. {str(e)}")
        return

def ask_submission(id:str): # Retrieves upload URL
    headers = { 'x-app-key': APP_KEY, 'Content-Type': 'application/json' }
    data = { "id": id }
    try:
        response = requests.post(BASE_URL+POST_PRESUBMIT_RESULT, headers=headers, json=data)
        response = response.json()
        if response['code'] != 201:
            print(f"Could not retrieve submission url.\n\tError code : {response['code']}\n\tMessage: {response['message']}")
            return STATUS.FAIL, "Failed to retrieve submission url"
        return response['data'], None
    except requests.exceptions.RequestException as e:
        print(f"Error while asking to submit. {str(e)}")
        return STATUS.FAIL, f"Error while asking to submit. {str(e)}"

def upload_result(r, result_path, id): # Uploads training result
    # Single file
    headers = { 'x-app-key': APP_KEY, 'Content-Type': 'application/json' }

    with open(result_path, 'rb') as file:
        file_content = file.read()
    files = {'file': (os.path.basename(result_path), file_content)}
    try: 
        response = requests.put(r["uploadUrl"], headers=headers, files=files)
        print(response)
        if response.status_code != 200:
            print(f"Could not upload files to the provided url.")
            return STATUS.FAIL, "Could not upload files to the provided url"
    except requests.exceptions.RequestException as e:
        print(f"Error while uploading files. {str(e)}")
        return STATUS.FAIL, f"Error while uploading files. {str(e)}"
    finally: 
        if os.path.exists(f'{TRAINING_DATA_PATH}/{id}'):
            shutil.rmtree(f'{TRAINING_DATA_PATH}/{id}')
    return STATUS.DONE, "Finished training and uploaded results."

def notify_finished(id:str, status:STATUS, message:str, fileKey:str, meta:Dict[str, Any] ): # Notifies training has finsihed
    headers = { 'x-app-key': APP_KEY, 'Content-Type': 'application/json' }
    data = { "id": id, "status": status, "message": message, "fileKey":fileKey, "meta":meta }
    try:
        response = requests.post(BASE_URL+POST_RESULT, headers=headers, json=data)
        response = response.json()
        if response["code"] != 201:
            print(f"Could not post result.\n\tError code : {response['code']}\n\tMessage: {response['message']}")
            return STATUS.FAIL
        return STATUS.DONE
    except requests.exceptions.RequestException as e:
        print(f"Error while requesting to post result. {str(e)}")
        return STATUS.FAIL
    finally:
        # Removes training data
        if os.path.exists(f'{TRAINING_DATA_PATH}/{id}'):
            shutil.rmtree(f'{TRAINING_DATA_PATH}/{id}')

# TODO: Use this to send results
def send_results(id, result_path, meta):
    r, msg = ask_submission(id)
    if r != STATUS.FAIL:
        fileKey = r["key"]
        r, msg = upload_result(r, result_path, id)
    notify_finished(id, r, msg, fileKey, meta)
'''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6000, debug=True)
