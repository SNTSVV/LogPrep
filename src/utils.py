import os
from datetime import datetime

import logging
logger = logging.getLogger(__name__)


def common_logger(name: str, level='DEBUG'):
    if not os.path.exists('_logs'):
        os.makedirs(os.path.join('_logs'))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_id = timestamp + f'_{os.getpid()}'
    log_file = os.path.join('_logs', f'{name}_{log_id}.log')
    logging.basicConfig(filename=log_file,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    lg = logging.getLogger()
    if level == 'DEBUG':
        lg.setLevel(logging.DEBUG)
    elif level == 'INFO':
        lg.setLevel(logging.INFO)
    return lg, log_id
