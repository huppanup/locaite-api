BASE_URL = "https://locaite-dev.collectiv.co"

APP_KEY = "TnO9DTVvdLlJ3o66TPUaW7XiCcmnRg4w" # TODO: Replace with actual app key

GET_TRAINING_SOURCE = "/api/service/crowd/training/source"
PUT_TRAINING_STATUS = "/api/service/crowd/training/status"
POST_PRESUBMIT_RESULT = "/api/service/crowd/training/presubmit"
POST_RESULT = "/api/service/crowd/training/finish"

TRAINING_DATA_PATH = "../data"
LOGFILE_PATH = '../locaite_output.log'


class STATUS:
    FAIL = "FAIL"
    TRAINING = "TRAINING"
    DONE = "DONE"  # Add more statuses as needed
