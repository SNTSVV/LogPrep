"""
Log pattern
    (KEYWORD) date, month, time: related to timestamp; used to `log_cleaning` in pre_processing
    (KEYWORD) level: log level (e.g., INFO, DEBUG); used to `level_filtering` in pre_processing
    (KEYWORD) module: a sub-system that encapsulates a set of components; used to `module_filtering` in pre_processing
    (KEYWORD) component: a set of related functions (usually a single program file); used to `log_projection`
    (KEYWORD) message: a log message message; used to `template_extraction` and so on in pre_processing
    (KEYWORD) jobID: a job (i.e., a set of processes) ID; used to `log_slicing` in pre-processing
    (KEYWORD) *_ext: try to match as much as possible (advanced option)
    Other elements, such as <node> or <port>, are not used in log-based analysis

"""

settings = {

    'HDFS': {
        'log_format': '<date> <time> <process> <level> <component>: <message>',
        'pre_patterns': [],
        'log_dir': 'dataset/sample/HDFS',
        'template_dir': 'dataset/sample/HDFS',
        'file_ext': '.log'
    },

    'Apache': {
        'log_format': '',
        'pre_patterns': [],
        'log_dir': 'dataset/sample/Apache',
        'template_dir': 'dataset/sample/Apache',
        'file_ext': '.csv'
    },

}