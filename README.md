# LogPrep

This is a simple log preprocessing tool which takes as input a set of either unstructured or structured logs
and returns a single structured log (csv), optionally including log message template information.

### Author
- Donghwan Shin (donghwan.shin@uni.lu)

### Key Functionalities

- convert a set of unstructured logs into a structured log according to a given log format
- extract log message templates using [Drain3](https://github.com/IBM/Drain3)
- map previously extracted templates to a set of log messages

# How to use

### Requirements

- pandas
- natsort
- drain3
- tqdm

### Install

You can simply install the required python libraries using `pip`, or just execute the following commands on your terminal, one by one:
```sh
git clone THIS_REPOSITORY_ADDRESS LogPrep
cd LogPrep
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Input

The main inputs are:
* Log file(s)
* Setup file, including the log format to be used in case of handling unstructured logs
* (optional) Template file containing previously generated templates

All inputs are placed under `/dataset/GROUP/SYSTEM`, where
* `GROUP`: a group name (e.g., `sample`);
* `SYSTEM`: a system/dataset name (e.g.,  `HDFS`).

*NOTE*: Each group must have a proper setup file `/dataset/GROUP/setup.py` that specifies the details for all systems under the group. 
For instance, an example setup file for the sample group (i.e., `/dataset/sample/setup.py`) looks like this:
```python
settings = {

    'HDFS': {
        'log_format': '<date> <time> <process> <level> <component>: <message>',
        'pre_patterns': [],
        'log_dir': 'dataset/sample/HDFS',
        'template_dir': 'dataset/sample/HDFS',
        'file_ext': '.log'
    },

    'Apache': {
        'log_format': '',  # no need since the file we are going to read is .csv
        'pre_patterns': [],
        'log_dir': 'dataset/sample/Apache',
        'template_dir': 'dataset/sample/Apache',
        'file_ext': '.csv'
    },

}
```
* `log_format`: the log format manually identified by looking at the corresponding log lines
* `pre_patterns`: manually identified patterns to be used for template identification
* `log_dir`: the directory where the log file(s) is located
* `template_dir`: the directory where the template file (csv; containing previously identified templates) is located
* `file_ext`: the log file extension; the tool automatically traverses all sub-directories under `log_dir` and reads all files whose extension matches to `file_ext`

### Parameters

```shell script
(venv) ➜ LogPrep git:(master) ✗ python LogPrep.py -h           
usage: LogPrep.py [-h] [-s SYSTEM] [-it] [-mlt] [-dm]

options:
  -h, --help            show this help message and exit
  -s SYSTEM, --system SYSTEM
                        System name
  -it, --identify_templates
                        Identify templates (default: false)
  -mlt, --merge_logs_and_templates
                        Merge logs and templates
  -dm, --drop_message   Drop messages in the structured log
```

### Output
The main outputs are:
* `-it`: a structured log file (csv) with templates newly identified by Drain3
* `-dm`: a structured log file (csv) with templates newly identified by Drain3, without original messages; this is just to reduce the file size
* `-mlt`: a structured log file (csv) merging the original logs (either structured or unstructured) and existing templates (csv)

# Example Use Cases

### UC1: convert an unstructured log into a structured one without identifying templates
1. Make sure `config.py` refers to the correct setup file;
    * The file should contain `from dataset.sample.setup import settings` in this example
2. Run the tool without any optional parameters
    * command: `python LogPrep.py -s HDFS`
3. Check the output under `/output/HDFS`
    * This time, the tool will generate `HDFS.csv` (i.e., a structured log file) 
    
### UC2: convert an unstructured log into a structured one and identify templates using Drain3
1. Make sure `config.py` refers to the correct setup file;
    * The file should contain `from dataset.sample.setup import settings` in this example
2. Run the tool with `-it`
    * command: `python LogPrep.py -s HDFS -it`
    * if you want to drop messages to reduce the resulting file size, you can additionally use `-dm`
3. Check the output under `/output/HDFS`
    * This time, the tool will generate `HDFS_structured_logs_drain3.csv` (i.e., a structured log file containing Drain3-generated templates) and `HDFS_templates_drain3.csv` (i.e., a list of templates identified by Drain3)

### UC3: convert an unstructured log into a structured one and match existing templates to individual messages
1. Make sure `config.py` refers to the correct setup file;
    * The file should contain `from dataset.sample.setup import settings` in this example
2. Run the tool with `-mlt`
    * command: `python LogPrep.py -s HDFS -mlt`
3. Check the output under `/output/HDFS`
    * This time, the tool will generate `HDFS_structured_logs.csv` (i.e., a structured log file containing previously generated templates)

### UC4: identify templates using Drain3 from a structured log
1. Make sure `config.py` refers to the correct setup file;
    * The file should contain `from dataset.sample.setup import settings` in this example
2. Run the tool with `-it`
    * command: `python LogPrep.py -s Apache -it`
    * Note that the Apache log is already structured (i.e., `Apache-sample.csv`)
    * if you want to drop messages to reduce the resulting file size, you can additionally use `-dm`
3. Check the output under `/output/Apache`
    * This time, the tool will generate `Apache_structured_logs_drain3.csv` (i.e., a structured log file containing Drain3-generated templates) and `Apache_templates_drain3.csv` (i.e., a list of templates identified by Drain3)


# Licensing

LogPrep is (c) 2022 University of Luxembourg and licensed under the MIT license.

The sample logs under `/dataset/sample` are from [LogHub](https://github.com/logpai/loghub); they are [freely available](https://github.com/logpai/loghub#license) and [distributable](https://github.com/logpai/loghub/issues/21#issuecomment-1170686552) for research purposes.

