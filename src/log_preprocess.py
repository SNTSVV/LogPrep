import os
import re
import time
import json
import shutil
import pandas as pd
from natsort import natsorted
from drain3 import TemplateMiner

from tqdm import tqdm

import logging
logger = logging.getLogger(__name__)
templates_dict = {}


import mmap

def get_num_lines(file_path):
    fp = open(file_path, "r+")
    buf = mmap.mmap(fp.fileno(), 0)
    lines = 0
    while buf.readline():
        lines += 1
    return lines


def get_templates_using_drain3(
        system: str, log_dir: str, file_ext: str, log_format: str, output_dir: str,
        drop_message: bool = False
    ):
    """
    Identify templates from the given logs.
    The generated templates are saved as a csv file under the specified output_dir.
    It also generates structured log file.

    :param system: system name
    :param log_dir: input log dir
    :param file_ext: input log file extension
    :param log_format: input log format (e.g., r'<date> <time> <level> <component>: <message>')
    :param output_dir: output template directory
    :param drop_message: whether drop messages in the structured file or not
    :return: templates (pandas.DataFrame)
    """
    print('Generating templates ...')
    init_time = time.time()

    # get logs_df
    logs_df = get_logs_df(system=system, log_dir=log_dir, file_ext=file_ext, log_format=log_format)

    # extract templates
    template_miner = TemplateMiner()
    line_count = 0
    start_time = time.time()
    batch_start_time = start_time
    batch_size = 100000
    logs_df['tid'] = ''
    for index, row in logs_df.iterrows():
        result = template_miner.add_log_message(row['message'])
        logs_df.at[index, 'tid'] = result['cluster_id']

        line_count += 1
        if line_count % batch_size == 0:
            time_took = time.time() - batch_start_time
            rate = batch_size / time_took
            print(f"Processing line: {line_count}, rate {rate:.1f} lines/sec, "
                  f"{len(template_miner.drain.clusters)} clusters so far.")
            batch_start_time = time.time()
        if result["change_type"] != "none":
            result_json = json.dumps(result)
            # logger.info(f"Input ({line_count}): " + line)
            # logger.info("Result: " + result_json)

    time_took = time.time() - start_time
    rate = line_count / time_took
    print(f"Done processing logs. Total of {line_count} lines, rate {rate:.1f} lines/sec, "
          f"{len(template_miner.drain.clusters)} clusters")
    template_miner.profiler.report(0)

    # remove redundant templates and sort the results
    templates = []
    for cluster in template_miner.drain.clusters:
        templates.append([cluster.cluster_id, cluster.get_template()])
    # templates = natsorted(templates, key=lambda x: x[0])
    print(f'Total number of templates generated: {len(templates)}')

    # save templates
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    templates_df = pd.DataFrame(templates, columns=['tid', 'template'])
    templates_df.to_csv(os.path.join(output_dir, f'{system}_templates_drain3.csv'), index=False)

    # save structured log
    logs_df = logs_df.join(templates_df.set_index('tid'), on='tid')
    logs_df['values'] = '[]'  # TODO: update drain3 to have matching values for each message
    if drop_message:
        logs_df = logs_df.drop(columns=['message'])
    logs_df.to_csv(os.path.join(output_dir, f'{system}_structured_logs_drain3.csv'), index=False)

    print('Generating templates done. [Time taken: %.3f sec]' % (time.time() - init_time))

    return len(templates)


def get_structured_logs_df(system: str, log_dir: str, file_ext: str, log_format: str, template_dir: str,
                           output_dir: str,
                           log_split_keyword: str = None):
    """
    Return a structured_logs_df (dataframe) from log files and already generated templates.

    :param system: system name
    :param log_dir: input log dir
    :param file_ext: input log file extension
    :param log_format: input log format
    :param template_dir: input template dir
    :param output_dir: output dir
    :param log_split_keyword: log splitting keyword
    :return: structured log (pandas.DataFrame) and templates (pandas.DataFrame)
    """
    print('Generating structured_logs_df ...')
    start_time = time.time()

    # generate logs_df
    logs_df = get_logs_df(
        system=system,
        log_dir=log_dir,
        file_ext=file_ext,
        log_format=log_format,
        log_split_keyword=log_split_keyword
    )

    # generate templates_df
    templates_df = read_templates_into_df(system=system, template_dir=template_dir)

    # prepare templates_dict
    templates_dict.clear()
    templates_df['re'] = templates_df['template'].map(generate_pattern_from_template)
    for index, row in templates_df.iterrows():
        templates_dict[row['re']] = (index, row['template'])

    # parsing using _find_matching_template()
    # TODO: how to improve the performance of find_matching_template? at least how to see the percentage?
    # FIXME: how to avoid using a global variable?
    logs_df['tid'], logs_df['template'], values = zip(*logs_df['message'].map(find_matching_template))
    logs_df['values'] = pd.Series(values)  # to avoid VisibleDeprecationWarning (ndarray from ragged nested sequences)
    logger.info('_find_matching_template() is done')

    # remove template-non-matching messages
    num_template_non_matching = len(logs_df[logs_df.template == '__NOT_MATCHING__'])
    if num_template_non_matching > 0:  # FOR DEBUGGING
        non_matching_logs_df = logs_df[logs_df.template == '__NOT_MATCHING__'] \
            .sample(n=min(num_template_non_matching, 100), random_state=1)
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        non_matching_logs_df.to_csv(os.path.join(output_dir, f'{system}_non_template_msgs_100.csv'), index=False)
    logger.info(f"Total number of template-non-matching messages: {num_template_non_matching}")
    logs_df = logs_df[logs_df.template != '__NOT_MATCHING__']
    templates_df = logs_df[['tid', 'template']].drop_duplicates().set_index('tid')
    templates_df.reindex(index=natsorted(templates_df.index))

    logger.info(f"Total number of logs in structured logs: {len(logs_df['logID'].unique())}")
    logger.info(f'Total number of log entries in structured logs: {len(logs_df)}')

    # save structured_logs_df
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    logs_df.to_csv(os.path.join(output_dir, f'{system}_structured_logs.csv'), index=False)
    print('Generating structured_logs_df done. [Time taken: %.3f sec]' % (time.time() - start_time))

    return logs_df, templates_df


def get_logs_df(system: str, log_dir: str, file_ext: str, log_format: str, log_split_keyword: str = None):
    """
    Get structured log (without templates) as a pandas.DataFrame.

    :param system: system name
    :param log_dir: input log dir
    :param file_ext: input log file extension
    :param log_format: input log format (e.g., "<date> <time> <level> <component>: <message>")
    :param log_split_keyword: log file splitting keyword (e.g., "initialize logging")
    :return: structured log (without templates) in the form of pandas.DataFrame
    """

    # split log files if specified
    if log_split_keyword is not None:
        log_dir = split_log(system=system, log_dir=log_dir, log_split_keyword=log_split_keyword)

    # collect all log files to read
    log_files = get_log_files_under_dir(log_dir=log_dir, file_ext=file_ext)

    # convert log files into a dataframe
    logs_df = load_logs_into_df(log_format=log_format, log_files=log_files, file_ext=file_ext)
    return logs_df


def get_log_files_under_dir(log_dir: str, file_ext='.log'):
    """
    Return a list of log files (with path, as tuple) under the given log_dir.

    :param log_dir: the root directory for searching log files
    :param file_ext: (optional) log file extension; `.log` by default
    :return: a (sorted) list of tuples composed of (log_path, log_file)
    """
    raw_logs = []
    for root, dirs, files in os.walk(log_dir):
        for file in files:
            if file.endswith(file_ext):
                raw_logs.append((root, file))
                logger.debug('collected log file: %s/%s' % (root, file))
    print('Total number of logs: %d' % len(raw_logs))

    if len(raw_logs) == 0:
        print(f'ERROR: No log files detected under: {log_dir}')
        exit(0)

    return natsorted(raw_logs)


def load_logs_into_df(log_format: str, log_files: list, file_ext: str):
    """
    Parse log files according to the given log_format and return a dataframe.

    :param log_format: log format for parsing log files
    :param log_files: log files to read
    :param file_ext: target log file extension (e.g., .log, .csv)
    :return: dataframe
    """
    header, pattern = generate_pattern_from_log_format(log_format)

    log_id = 1
    log_dfs = []
    for path, file in log_files:
        # process each log file, one by one

        if file_ext.endswith('.csv'):
            # simply read the csv file since it's already structured
            log_df = pd.read_csv(os.path.join(path, file))
        else:
            # start processing the given log file using `header` and `pattern`
            if 'message' not in header:
                print(f'ERROR: <message> is not in log_format={log_format}')
                exit(-1)

            log_lines = []
            with open(os.path.join(path, file), 'r', errors='replace') as log:
                # for line in log:
                for line in tqdm(log, total=get_num_lines(os.path.join(path, file))):
                    m = re.match(pattern, line.strip())
                    if m:
                        log_line = [m.group(h) for h in header]
                        log_lines.append(log_line)
                    else:
                        logger.debug(f'Skip non-matched log_line={line.strip()}')
            log_df = pd.DataFrame(log_lines, columns=header)

        # strip unnecessary white spaces in messages
        log_df['message'] = log_df['message'].str.strip()
        length = log_df['message'].size

        # add logID and lineID columns if needed
        if 'logID' not in header and 'logID' not in log_df.columns and 'lineID' not in log_df.columns:
            log_df.insert(0, 'lineID', None)
            log_df['lineID'] = [i + 1 for i in range(length)]
            log_df.insert(0, 'logID', log_id)
            log_id += 1

        # append log_df to logs_df
        log_dfs.append(log_df)
        logger.info(f'loaded log file (length={length}): {os.path.join(path, file)}')

    logs_df = pd.concat(log_dfs, ignore_index=True)
    print(f'Total number of log messages in raw logs: %d' % len(logs_df))

    return logs_df


def generate_pattern_from_log_format(log_format: str):
    header = re.findall(r'<(\S+?)>', log_format)
    pattern = re.sub(r'(<\S+?>)', r'(?P\1.+?)', log_format)
    pattern = re.sub(r'<(\S+)_ext>\.\+\?', r'<\1_ext>.+',
                     pattern)  # bypassing the issue of `test_generate_pattern_from_format_Zookeeper`
    pattern = re.sub(r'\s+', r'\\s+', pattern)
    pattern = '^' + pattern + '$'
    return header, pattern


def split_log(system: str, log_dir: str, log_split_keyword: str, output_dir: str = None):
    print('Splitting logs ...')
    start_time = time.time()

    if output_dir:
        split_log_dir = output_dir
    else:
        split_log_dir = os.path.join(log_dir, 'split')

    # remove existing splitting logs
    if os.path.exists(split_log_dir):
        shutil.rmtree(split_log_dir)

    # initialize
    os.makedirs(split_log_dir)
    log_id = 1
    read_lines = list()

    # split a single log file containing multiple execution logs
    for path, log_file in get_log_files_under_dir(log_dir):
        with open(os.path.join(path, log_file), 'r', errors='replace') as log:
            for line in log:
                if log_split_keyword in line and len(read_lines) > 0:
                    # write a new log (file)
                    write_new_log(system=system, log_id=log_id, log_lines=read_lines, split_log_dir=split_log_dir)

                    # initialize read_lines and update log_id
                    read_lines = list()
                    log_id += 1

                read_lines.append(line)

            # write remaining read_lines
            if len(read_lines) > 0:
                write_new_log(system=system, log_id=log_id, log_lines=read_lines, split_log_dir=split_log_dir)

    print('Splitting logs done. [Time taken: %.3f sec]' % (time.time() - start_time))
    return split_log_dir


def write_new_log(system: str, log_id: int, log_lines: list, split_log_dir: str):
    new_log = os.path.join(split_log_dir, f'{system}_{log_id}.log')
    with open(new_log, 'w') as f:
        for line in log_lines:
            f.write(line)
    logger.debug(f'{new_log} (size={len(log_lines)})')


def read_templates_into_df(system: str, template_dir: str):
    """
    Read templates from `self.template_dir/{self.system}_templates.csv`.
    Exit here if there is no such file.
    """

    templates_df = None

    # read templates (if exist)
    template_file = os.path.join(template_dir, f'{system}_templates.csv')
    if os.path.isfile(template_file):
        templates_df = pd.read_csv(os.path.join(template_file), index_col='tid')
        print(f'Total number of templates loaded: {len(templates_df)}')
        logger.info(f'Total number of templates loaded: {len(templates_df)}')
    else:
        print(f'ERROR: No such file: {template_file}')
        exit(0)

    if 'template' not in templates_df.columns:
        print(f'ERROR: {template_file} has no columns `tid` and `template`')
        exit(0)

    return templates_df


def generate_pattern_from_template(template: str):
    escaped = re.escape(template)
    spaced_escape = re.sub(r'\\\s+', "\\\s+", escaped)
    spaced_escape = re.sub(r'<[A-Z]{1,3}>', r'<\*>', spaced_escape)  # substitue <NUM> or <ID> into <*>
    return "^" + spaced_escape.replace(r"<\*>", r"(.*?)") + "$"  # a single <*> can consume multiple tokens


def find_matching_template(message):
    """

    :param message: a log message (only the message)
    :return: (tid, template, parameter_list)
    """
    for r in sorted(templates_dict.keys(), key=lambda x: len(x), reverse=True):
        m = re.match(r, message)
        if m:
            tid, template = templates_dict[r]
            if '<*>' in template:
                return tid, template, list(m.groups())
            else:
                return tid, template, []
    logger.debug(f'No template: {message}')
    return '-', '__NOT_MATCHING__', '-'
